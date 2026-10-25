"""Generate a machine-specific IPC manifest in the isolated profile only."""
import json
import os
import struct
import zlib
from pathlib import Path
import sys

root = Path(__file__).resolve().parents[1]
# KiCad 10 appends KiCad/<major.minor> to KICAD_DOCUMENTS_HOME.
target = root / '.runtime' / 'documents' / 'KiCad' / '10.0' / 'plugins' / 'koa_ipc_probe'
target.mkdir(parents=True, exist_ok=True)
# Original geometric test icon, generated locally without external assets.
def chunk(kind, data):
    return struct.pack('!I', len(data)) + kind + data + struct.pack('!I', zlib.crc32(kind + data))
rows = b''.join(b'\x00' + b''.join(bytes((255, 255, 255, 255) if (10 <= x <= 13 or 10 <= y <= 13) else (38, 102, 162, 255)) for x in range(24)) for y in range(24))
(target / 'probe.png').write_bytes(b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('!2I5B', 24, 24, 8, 6, 0, 0, 0)) + chunk(b'IDAT', zlib.compress(rows)) + chunk(b'IEND', b''))
manifest = {
    "identifier": "org.kicad-open-assistant.feasibility",
    "name": "KiCad Open Assistant IPC probe",
    "description": "Offline test of external action launch; no embedding claim",
    "runtime": {"type": "exec"},
    "actions": [{
        "identifier": "launch-companion-probe",
        "name": "Open Assistant IPC companion probe",
        "description": "Launch a separate offline window to test API plugin registration",
        "show-button": True,
        "icons-light": ["probe.png"],
        "icons-dark": ["probe.png"],
        "scopes": ["pcb", "schematic"],
        # KiCad rejects absolute entrypoints. This local probe references the
        # already installed interpreter; it is not a distributable manifest.
        "entrypoint": os.path.relpath(Path(sys.executable).with_name('pythonw.exe'), target),
        "args": [str(root / 'prototype' / 'ipc_launch_probe.py')],
    }],
}
(target / 'plugin.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
print(target / 'plugin.json')
