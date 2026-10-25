"""Railway adapter: require a volume, prepare one directory, then drop root."""
import os
from pathlib import Path
import sys


def prepare():
    volume = Path("/data")
    database = volume / "koa" / "ledger.sqlite3"
    if sys.platform != "linux" or volume.is_symlink() or not volume.is_mount():
        raise RuntimeError("A persistent volume must be mounted at /data.")
    if os.environ.get("KOA_LEDGER") != str(database):
        raise RuntimeError("Set KOA_LEDGER=/data/koa/ledger.sqlite3.")
    if database.parent.is_symlink() or database.is_symlink():
        raise RuntimeError("The accounting directory must not be a symbolic link.")
    if not database.exists() and os.environ.get("KOA_SPONSORED_ENABLED") == "true":
        raise RuntimeError("Missing ledger: initialize while disabled; never recreate funded capacity.")
    os.umask(0o077)
    database.parent.mkdir(mode=0o700, exist_ok=True)
    if os.geteuid() == 0:
        # Railway initially mounts volumes as root. No recursive ownership changes.
        os.chown(database.parent, 10001, 10001)
        os.chmod(database.parent, 0o700)
        os.setgroups([])
        os.setgid(10001)
        os.setuid(10001)
    if os.geteuid() != 10001 or os.getegid() != 10001:
        raise RuntimeError("The HTTP service must run as UID/GID 10001.")
    from .ledger import Ledger
    Ledger(database).initialize()  # Idempotent; never resets charges or the kill switch.


def main():
    try:
        prepare()
    except Exception:
        # No raw environment values, filesystem exceptions or credentials in logs.
        raise SystemExit("Hosting preflight failed. Check the volume, ledger path, disabled first boot and UID configuration.") from None
    os.execv(sys.executable, [sys.executable, "-m", "uvicorn",
             "kicad_open_assistant.service.app:create_app", "--factory",
             "--host", "0.0.0.0", "--port", "8000", "--no-access-log",
             "--no-proxy-headers", "--limit-concurrency", "8",
             "--timeout-keep-alive", "5", "--timeout-graceful-shutdown", "5"])


if __name__ == "__main__":
    main()
