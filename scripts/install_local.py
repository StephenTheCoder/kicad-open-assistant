"""Install a built PCM archive into an explicitly selected KiCad profile.

Normal users should use PCM Install from File. This helper is for isolated tests
or a deliberate manual installation. Existing directories are never overwritten.
"""
import argparse
from pathlib import Path
import zipfile


def install(archive_path, profile):
    target = profile.resolve() / "10.0/scripting/plugins/kicad_open_assistant_plugin"
    if target.exists():
        raise SystemExit("Existing installation preserved. Choose a fresh test profile or uninstall it explicitly first.")
    with zipfile.ZipFile(archive_path) as archive:
        members = [entry for entry in archive.infolist() if entry.filename.startswith("plugins/") and not entry.is_dir()]
        if not members:
            raise SystemExit("Archive contains no plugin.")
        planned = []
        for entry in members:
            relative = Path(entry.filename.removeprefix("plugins/"))
            destination = (target / relative).resolve()
            if not destination.is_relative_to(target) or entry.file_size > 100 * 1024 * 1024:
                raise SystemExit("Invalid archive member.")
            planned.append((entry, destination))
        for entry, destination in planned:
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(archive.read(entry))
    print(target)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    parser.add_argument("--profile", type=Path, required=True)
    args = parser.parse_args()
    install(args.archive, args.profile)
