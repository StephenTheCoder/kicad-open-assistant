"""Audit tracked/current files, every reachable Git blob, and release ZIP members.

Reports locations and categories only, never matched credential values.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parents[1]
PATTERNS = {
    "OpenAI credential": re.compile(rb"sk-(?:proj-|svcacct-)?[A-Za-z0-9_-]{24,}"),
    "GitHub credential": re.compile(rb"(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,})"),
    "private key": re.compile(rb"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "AWS access identifier": re.compile(rb"AKIA[A-Z0-9]{16}"),
}
FORBIDDEN = {".runtime", "work", ".venv", "graphify-out", "kicad-plugin-investigation", ".git"}
# Pillow's unmodified embedded default font contains an AWS-shaped base64 run.
# Exact file/category/hash exception only; a changed wheel must be reviewed again.
FONT_HASH = "0b8494851d5cd92126e88903fafdd505f163f4f454d72a1dacba0d141a4b123a"


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT, stderr=subprocess.DEVNULL)


def check(name, data, problems, path_policy=True):
    parts = Path(name).parts
    if path_policy and (any(p in FORBIDDEN for p in parts) or Path(name).name in {".env", "rea-evidence.json", "kicad_ai_plugin.zip"} or Path(name).suffix in {".token", ".secret", ".sqlite3"}):
        problems.append({"location": name, "category": "private or investigation path"})
    for label, pattern in PATTERNS.items():
        if pattern.search(data):
            if name == "plugins/vendor/PIL/ImageFont.py" and label == "AWS access identifier" and hashlib.sha256(data).hexdigest() == FONT_HASH:
                continue
            problems.append({"location": name, "category": label})


def audit(archive=None):
    problems, count, objects = [], 0, 0
    for raw in git("ls-files", "-z").split(b"\0"):
        if not raw:
            continue
        name = raw.decode()
        path = ROOT / name
        if path.is_file():
            check(name, path.read_bytes(), problems)
            count += 1
        # Audit the index separately: a working-tree fix must not hide an old staged secret.
        check("index:" + name, git("show", ":" + name), problems, path_policy=False)
    for line in git("rev-list", "--objects", "--all").decode().splitlines():
        fields = line.split(" ", 1)
        oid, name = fields[0], fields[1] if len(fields) > 1 else ""
        if git("cat-file", "-t", oid).strip() == b"blob":
            check("history:" + name, git("cat-file", "blob", oid), problems, path_policy=False)
            # Apply the actual historical path policy as well.
            historical_paths = []
            check(name, b"", historical_paths)
            problems.extend({"location": "history:" + p["location"], "category": p["category"]} for p in historical_paths)
            objects += 1
    members = 0
    if archive:
        with zipfile.ZipFile(archive) as bundle:
            for entry in bundle.infolist():
                if not entry.is_dir():
                    check(entry.filename, bundle.read(entry), problems)
                    members += 1
    report = {"tracked_files": count, "reachable_git_blobs": objects, "archive_members": members, "findings": problems,
              "scope_note": "Heuristic credential scan plus explicit private-path policy. Original-work provenance and screenshots require human/agent review too."}
    print(json.dumps(report, indent=2))
    if problems:
        raise SystemExit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path)
    audit(parser.parse_args().archive)
