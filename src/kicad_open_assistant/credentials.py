"""Windows Credential Manager; credentials never fall back to a local file."""
import ctypes
from ctypes import wintypes
import hashlib
import sys
from .policy import AppError


def target(mode="personal", endpoint=""):
    return "KiCadOpenAssistant/" + ("OpenAI" if mode == "personal" else "Sponsored/" + hashlib.sha256(endpoint.encode()).hexdigest())


class Credential(ctypes.Structure):
    _fields_ = [("Flags", wintypes.DWORD), ("Type", wintypes.DWORD), ("TargetName", wintypes.LPWSTR),
                ("Comment", wintypes.LPWSTR), ("LastWritten", wintypes.FILETIME), ("CredentialBlobSize", wintypes.DWORD),
                ("CredentialBlob", ctypes.POINTER(ctypes.c_ubyte)), ("Persist", wintypes.DWORD),
                ("AttributeCount", wintypes.DWORD), ("Attributes", ctypes.c_void_p), ("TargetAlias", wintypes.LPWSTR), ("UserName", wintypes.LPWSTR)]


def api():
    if sys.platform != "win32":
        raise AppError("credential_store", "This release requires Windows Credential Manager.")
    lib = ctypes.WinDLL("Advapi32.dll", use_last_error=True)
    lib.CredReadW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, ctypes.POINTER(ctypes.POINTER(Credential))]
    lib.CredReadW.restype = wintypes.BOOL
    lib.CredWriteW.argtypes = [ctypes.POINTER(Credential), wintypes.DWORD]
    lib.CredWriteW.restype = wintypes.BOOL
    lib.CredFree.argtypes = [ctypes.c_void_p]
    lib.CredDeleteW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD]
    lib.CredDeleteW.restype = wintypes.BOOL
    return lib


def read(name):
    lib = api()
    pointer = ctypes.POINTER(Credential)()
    if not lib.CredReadW(name, 1, 0, ctypes.byref(pointer)):
        if ctypes.get_last_error() == 1168:
            return None
        raise AppError("credential_store", "Windows Credential Manager could not read this application's credential.")
    try:
        return ctypes.string_at(pointer.contents.CredentialBlob, pointer.contents.CredentialBlobSize).decode("utf-8")
    finally:
        lib.CredFree(pointer)


def write(name, secret):
    if not secret.strip() or len(secret.encode()) > 2400:
        raise AppError("credential", "Credential must contain 1–2400 UTF-8 bytes.")
    blob = (ctypes.c_ubyte * len(secret.encode())).from_buffer_copy(secret.encode())
    value = Credential(Type=1, TargetName=name, CredentialBlobSize=len(blob), CredentialBlob=blob, Persist=2, UserName="KiCad Open Assistant")
    try:
        if not api().CredWriteW(ctypes.byref(value), 0):
            raise AppError("credential_store", "Windows Credential Manager refused the credential. No file was written.")
    finally:
        ctypes.memset(blob, 0, len(blob))


def delete(name):
    lib = api()
    if not lib.CredDeleteW(name, 1, 0) and ctypes.get_last_error() != 1168:
        raise AppError("credential_store", "Could not remove the credential from Windows Credential Manager.")
