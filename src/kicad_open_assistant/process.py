"""Disposable workers: no network/parsing/SQLite on KiCad's GUI thread."""
import ctypes
from ctypes import wintypes
import json
from pathlib import Path
import subprocess
import sys
import threading


class WindowsJob:
    """Kernel-enforced process memory cap and kill-on-owner-close."""
    def __init__(self, process, memory=512 * 1024 * 1024):
        size = ctypes.c_size_t
        class Basic(ctypes.Structure):
            _fields_ = [("per_process", ctypes.c_int64), ("per_job", ctypes.c_int64), ("flags", wintypes.DWORD),
                        ("min_ws", size), ("max_ws", size), ("active", wintypes.DWORD), ("affinity", size),
                        ("priority", wintypes.DWORD), ("scheduling", wintypes.DWORD)]
        class IO(ctypes.Structure):
            _fields_ = [(name, ctypes.c_uint64) for name in ("read_ops", "write_ops", "other_ops", "read_bytes", "write_bytes", "other_bytes")]
        class Extended(ctypes.Structure):
            _fields_ = [("basic", Basic), ("io", IO), ("process_memory", size), ("job_memory", size), ("peak_process", size), ("peak_job", size)]
        self.kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        self.kernel.CreateJobObjectW.argtypes = [ctypes.c_void_p, wintypes.LPCWSTR]
        self.kernel.CreateJobObjectW.restype = wintypes.HANDLE
        self.kernel.SetInformationJobObject.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD]
        self.kernel.SetInformationJobObject.restype = wintypes.BOOL
        self.kernel.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
        self.kernel.AssignProcessToJobObject.restype = wintypes.BOOL
        self.kernel.CloseHandle.argtypes = [wintypes.HANDLE]
        self.handle = self.kernel.CreateJobObjectW(None, None)
        info = Extended()
        info.basic.flags = 0x100 | 0x2000  # PROCESS_MEMORY | KILL_ON_JOB_CLOSE
        info.process_memory = memory
        if not self.handle or not self.kernel.SetInformationJobObject(self.handle, 9, ctypes.byref(info), ctypes.sizeof(info)) or not self.kernel.AssignProcessToJobObject(self.handle, int(process._handle)):
            self.close()
            raise RuntimeError("Could not enforce worker resource limits")

    def close(self):
        if self.handle:
            self.kernel.CloseHandle(self.handle)
            self.handle = None


class Task:
    def __init__(self, python, command, callback, timeout=30):
        self.python, self.command, self.callback, self.timeout = python, command, callback, timeout
        self.process = None
        self.cancelled = threading.Event()
        self.thread = threading.Thread(target=self.run, daemon=True)

    def start(self):
        self.thread.start()
        return self

    def cancel(self):
        self.cancelled.set()
        self.kill()

    def kill(self):
        if self.process and self.process.poll() is None:
            try:
                self.process.kill()
            except OSError:
                pass

    def run(self):
        job, timer = None, None
        try:
            self.process = subprocess.Popen([str(self.python), "-I", str(Path(__file__).with_name("worker_entry.py"))], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                                            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0)
            if sys.platform == "win32":
                job = WindowsJob(self.process)
            if self.cancelled.is_set():
                self.process.kill()
                return
            # Start parsing only after the job has been assigned.
            timer = threading.Timer(self.timeout, self.kill)
            timer.daemon = True
            timer.start()
            self.process.stdin.write(json.dumps(self.command, ensure_ascii=False).encode("utf-8"))
            self.process.stdin.close()
            self.command = None  # Do not retain credential entry buffers.
            terminal = False
            while True:
                line = self.process.stdout.readline(31 * 1024 * 1024)
                if not line:
                    break
                if self.cancelled.is_set():
                    break
                event = json.loads(line)
                terminal |= event.get("type") in {"done", "result", "error"}
                self.callback(event)
            self.process.wait()
            if not terminal and not self.cancelled.is_set():
                self.callback({"type": "error", "code": "worker", "message": "Worker stopped or exceeded its time/memory limit. Reduce the input and try again."})
        except Exception:
            if not self.cancelled.is_set():
                self.callback({"type": "error", "code": "worker", "message": "Could not start the isolated worker. Verify installation and permissions."})
        finally:
            self.command = None
            if timer:
                timer.cancel()
            if self.process:
                if self.process.poll() is None:
                    self.process.kill()
                self.process.wait()
                for pipe in (self.process.stdin, self.process.stdout):
                    if pipe and not pipe.closed:
                        pipe.close()
            if job:
                job.close()
            if not self.cancelled.is_set():
                self.callback({"type": "exit"})
