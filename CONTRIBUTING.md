# Contributing

Keep changes original and MIT-compatible. Do not contribute proprietary plugin code, assets, conversations, configuration or investigation archives. Use only public API documentation and independently written implementations. See docs/PROVENANCE.md.

Use Python 3.11. Install the hash-locked client/service dependencies and the exact test tools listed in pyproject.toml. Run `python -m pytest`. Routine tests must mock inference; never require a real key or silently incur charges. Keep prompt/key/design data out of diagnostics and fixtures.

The core and service must not import wx or pcbnew. KiCad UI code delegates network/parsing/storage work to bounded workers. No model-generated code execution or board modification belongs in this advisory release. A new host version requires real KiCad runtime checks, not a mocked wx test.

Update acceptance evidence when behavior changes. Add meaningful regression tests for budget races, cancellation, history isolation, payload review, parser limits and credential boundaries. Review dependencies and licenses when updating locks. Never add runtime profiles, secrets or private designs to Git.

Build on Windows x64 with Python 3.11 and `python -m pip install --require-hashes --only-binary=:all: --target vendor -r requirements-client.lock`, then `python scripts/build_release.py`. Build twice and compare SHA-256. Run `python scripts/audit_release.py --archive dist/kicad-open-assistant-0.1.0-windows-kicad10.zip` after staging intended source and again after committing. Inspect every release member and full Git history before pushing. The heuristic scan supplements provenance review; it cannot prove absence of every possible secret.
