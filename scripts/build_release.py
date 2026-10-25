"""Build a deterministic PCM archive from an explicit allowlist and locked vendor tree."""
import argparse
import hashlib
import importlib.metadata
import json
from pathlib import Path
import tomllib
import zipfile

ROOT = Path(__file__).resolve().parents[1]
VERSION = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]["version"]


def entries():
    result = {"plugins/__init__.py": ROOT / "plugin/__init__.py", "plugins/LICENSE": ROOT / "LICENSE"}
    for path in (ROOT / "src/kicad_open_assistant").rglob("*.py"):
        if "service" not in path.relative_to(ROOT / "src").parts:
            result["plugins/lib/" + path.relative_to(ROOT / "src").as_posix()] = path
    vendor = ROOT / "vendor"
    if not vendor.is_dir():
        raise SystemExit("Install requirements-client.lock into vendor with hashes before building.")
    for path in vendor.rglob("*"):
        relative = path.relative_to(vendor)
        if not path.is_file() or "__pycache__" in relative.parts or path.suffix in {".pyc", ".pyo"} or relative.parts[0] in {"bin", "Scripts"}:
            continue
        if path.name in {".lock", "uv_cache.json", "direct_url.json", "INSTALLER", "REQUESTED", "RECORD"}:
            continue
        result["plugins/vendor/" + relative.as_posix()] = path
    for name in ("INSTALLATION.md", "PRIVACY.md", "SECURITY.md", "THIRD-PARTY-NOTICES.md"):
        path = ROOT / "docs" / name
        if not path.is_file():
            raise SystemExit("Missing release document: " + name)
        result["plugins/docs/" + name] = path
    return result


def build(destination):
    files = entries()
    inventory = []
    for distribution in sorted(importlib.metadata.distributions(path=[str(ROOT / "vendor")]), key=lambda d: d.metadata["Name"].lower()):
        inventory.append({"name": distribution.metadata["Name"], "version": distribution.version, "license": distribution.metadata.get("License-Expression") or distribution.metadata.get("License", "See bundled notices")})
    metadata = {"$schema": "https://go.kicad.org/pcm/schemas/v2", "name": "KiCad Open Assistant", "description": "Experimental advisory AI dock for Windows KiCad 10.0.7; local conversations and reviewed context.", "description_full": "Original open-source PCB-only dock. Personal OpenAI key or operator-sponsored access. Does not modify designs. Uses deprecated/internal KiCad interfaces; version-gated to Windows 10.0.7. No schematic UI integration. Third-party dependencies retain their licenses.", "identifier": "com.github.StephenTheCoder.kicad-open-assistant", "type": "plugin", "author": {"name": "KiCad Open Assistant contributors", "contact": {"web": "https://github.com/StephenTheCoder/kicad-open-assistant/issues"}}, "license": "MIT", "resources": {"homepage": "https://github.com/StephenTheCoder/kicad-open-assistant"}, "versions": [{"version": VERSION, "status": "testing", "kicad_version": "10.0", "kicad_version_max": "10.0", "runtime": "swig", "platforms": ["windows"]}]}
    data = {name: (path.read_bytes() if "plugins/vendor/" in name else path.read_text(encoding="utf-8-sig").replace("\r\n", "\n").encode("utf-8")) for name, path in files.items()}
    data["metadata.json"] = (json.dumps(metadata, indent=2) + "\n").encode()
    data["plugins/dependencies.json"] = (json.dumps(inventory, indent=2) + "\n").encode()
    sbom = {"bomFormat": "CycloneDX", "specVersion": "1.6", "version": 1,
            "metadata": {"component": {"type": "application", "name": "kicad-open-assistant", "version": VERSION}},
            "components": [{"type": "library", "name": row["name"], "version": row["version"],
                            "purl": "pkg:pypi/" + row["name"].lower().replace("_", "-") + "@" + row["version"]}
                           for row in inventory]}
    data["plugins/sbom.cdx.json"] = (json.dumps(sbom, indent=2) + "\n").encode()
    destination.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name in sorted(data):
            info = zipfile.ZipInfo(name, (2026, 10, 24, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            archive.writestr(info, data[name], compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
    digest = hashlib.sha256(destination.read_bytes()).hexdigest()
    destination.with_suffix(".zip.sha256").write_text(digest + "  " + destination.name + "\n", encoding="ascii")
    print(json.dumps({"artifact": destination.name, "files": len(data), "sha256": digest, "bytes": destination.stat().st_size}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "dist" / f"kicad-open-assistant-{VERSION}-windows-kicad10.zip")
    build(parser.parse_args().output)
