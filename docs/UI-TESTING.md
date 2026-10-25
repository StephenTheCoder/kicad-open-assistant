# Actual KiCad runtime validation

Install the unmodified PCM archive into a fresh profile first, launch the tested KiCad build, and open its registered action. Verify that the panel occupies PCB Editor's layout and resizes with it. A wx standalone window or a mocked UI is not evidence of this integration. Record the exact artifact hash and host versions.

Routine API scenarios may use the explicit **offline API fixture** in a second isolated installation:

```powershell
python scripts/prepare_ui_fixture.py dist/kicad-open-assistant-0.1.0-windows-kicad10.zip --profile .runtime/ui-fixture/config
```

This helper refuses an existing install. It substitutes only a worker entry point with mocked API/credential reads and visibly marks the dock. It preserves real KiCad/wx controls, extraction, process limits and local SQLite. The fixture does not read or change Windows credentials. Its code is under tests and is never included in the client archive. Set the generated `fixture-mode.json` to `stream`, `missing`, `network`, or `quota` between requests. The `stream` case uses the actual installed OpenAI SDK with a delayed mock HTTP body; sponsored fixture errors are synthetic. Backend enforcement is tested separately against the application service.

Launch with `KICAD_CONFIG_HOME` set to that profile, `KOA_DATA_HOME` to an isolated data directory and `KICAD_DOCUMENTS_HOME` to an isolated documents directory. Handle the initial KiCad preferences yourself. Use the helper's original attachment fixtures, never private designs.

Exercise create/rename/switch/delete/restart; attachment selection, edit/removal and all preview tabs; selected/unchecked board metadata; keyboard navigation, resize and hide/reopen; progressive output, switch during streaming and cancellation; missing credentials, network failure and quota errors. Check the originating conversation after switching back. Record each actual result and any limitation in RELEASE-VALIDATION.md.

The separate minimal live smoke uses a locally configured personal key, no history/designs/files, the prompt `Reply with OK.`, max 64 output tokens, and zero automatic retries. It requires explicit readiness from the operator. No fixture result counts as a successful live API call. Never photograph credential entry or publish raw runtime databases/configuration.
