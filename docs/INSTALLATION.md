# Installation and removal

This experimental release supports **Windows x64, KiCad 10.0.7, bundled Python 3.11.5 and wxPython 4.3.1** only. It uses the deprecated PCB Python interface and an internal dock manager. Other KiCad versions are rejected; schematic UI integration, Linux and macOS are not claimed.

Download the versioned `windows-kicad10.zip` asset and its SHA-256 file from the project's GitHub release. Compare with `Get-FileHash -Algorithm SHA256 <archive>`. In KiCad Manager open Plugin and Content Manager, choose **Install from File**, select the archive and apply changes. Restart PCB Editor. Open **Tools → External Plugins → KiCad Open Assistant**. The panel docks inside PCB Editor. Hide cancels work and hides the pane; invoking the action again reopens it. No browser or floating companion replaces a failed dock.

The archive includes its pinned dependency wheels' installed files, native Windows modules and licenses; no runtime dependency downloads are needed. KiCad supplies Python/wx. Use a disposable board before trusting an experimental host integration with working projects.

Open **Connection**. Personal mode accepts your own OpenAI key and stores it in Windows Credential Manager. Sponsored mode accepts the operator's HTTPS service address and a revocable application access token. Sponsored users never enter an OpenAI key. Use **Check allowance** to see the server's model and output cap, then match those settings before sending. Sponsored mode is unavailable until the operator configures and enables the backend.

Create or select a conversation, attach supported files if desired, and optionally select the active board summary. Use **Review and send** (Ctrl+Enter in the composer). Inspect text, destination and every image tab; Cancel returns to editing. **Inspect / edit** changes outgoing attachment text without editing the original file. The preview shows the immutable snapshot that will be sent. Limits and omissions are explicit; no background project crawl is performed.

The supported default model is `gpt-4.1-mini-2025-04-14` (Responses, streaming, text/image input). Personal mode allows another model ID; the user must have access and it must support the selected modalities. Unsupported model requests produce a connection/request error. The initial service allows only the reviewed default snapshot.

Conversations and reviewed attachment snapshots reside in `%LOCALAPPDATA%\KiCadOpenAssistant\conversations.sqlite3`. They persist across KiCad restarts and plugin updates. History selection defaults to eight previous completed messages, with a maximum of forty and 100,000 total text characters. Partial responses are preserved and labeled. Cancel closes the local worker/stream; provider computation already performed may still be billed.

Uninstall through PCM and restart KiCad. This intentionally keeps your conversation database and credentials. To remove credentials, use Connection's remove option before uninstalling, or remove only `KiCadOpenAssistant/...` entries manually in Windows Credential Manager. To erase conversations, use the app's Delete command or, after closing KiCad, delete your application data directory. Exports, backups and provider retention are separate.

For isolated validation, `python scripts/install_local.py <zip> --profile <empty-profile-directory>` installs the same archive without touching your normal profile. Launch KiCad with `KICAD_CONFIG_HOME` pointing at that directory and `KOA_DATA_HOME` at a separate local test data directory. The helper refuses to overwrite an existing install.

The archive follows KiCad PCM's package layout. GitHub publication and local installation do **not** imply acceptance into KiCad's official repository. Submission/review is separate.
