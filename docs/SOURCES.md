# Source register

Accessed 2026-10-24 unless stated otherwise. Source content is linked, not vendored. Runtime evidence takes precedence for what this installed build actually did; official docs establish supported contracts and roadmap boundaries.

| ID | Primary source | Use |
|---|---|---|
| K1 | https://dev-docs.kicad.org/en/apis-and-binding/ipc-api/for-addon-developers/ | IPC plugin lifecycle, separate processes, environment variables, documented editor support |
| K2 | https://dev-docs.kicad.org/en/apis-and-binding/pcbnew/ | Legacy ActionPlugin, PCB-only Python support, instability/deprecation |
| K3 | https://docs.kicad.org/10.0/en/pcbnew/pcbnew.html#scripting | Versioned scripting interface and installation paths |
| K4 | https://go.kicad.org/api/schemas/v1 | Manifest fields, executable runtime, action scopes; a declared scope is not proof of support |
| K5 | https://dev-docs.kicad.org/en/apis-and-binding/ipc-api/ | IPC design and compatibility intent |
| K6 | https://raw.githubusercontent.com/KiCad/kicad-source-mirror/10.0/common/paths.cpp | Actual Windows environment override and plugin directory layout |
| K7 | https://raw.githubusercontent.com/KiCad/kicad-source-mirror/10.0/common/api/api_plugin.cpp | Relative entrypoint validation; original manifest corrected from this constraint |
| K8 | https://raw.githubusercontent.com/KiCad/kicad-source-mirror/10.0/common/api/api_plugin_manager.cpp | External executable launch and instance environment handoff |
| O1 | https://developers.openai.com/api/docs/guides/streaming-responses | Responses SSE events |
| O2 | https://developers.openai.com/api/docs/guides/conversation-state | Local/manual history and store=false |
| O3 | https://developers.openai.com/api/docs/guides/file-inputs | PDF/document inputs, size and modality limits |
| O4 | https://developers.openai.com/api/docs/guides/your-data | Provider retention limitations |
| O5 | https://developers.openai.com/api/reference/python | Installed official SDK and Responses interface |
| O6 | https://developers.openai.com/api/docs/models/gpt-4.1-mini | Default pinned snapshot, modalities, context/output ceilings and accounting rates |
| K9 | https://dev-docs.kicad.org/en/addons/index.html | PCM layout and metadata; installed KiCad schema v2 validates the candidate |
| P1 | https://kicad.alttab.rs/pricing | Public hosted assistance description; numeric allowance unknown |
| P2 | https://kicad.alttab.rs/ | Early build/roadmap distinction captured in prior investigation |

The prior local investigation's FINDINGS.md and existing graphify graph were consulted without modification. They describe static observations, not executed product acceptance tests. A read-only check of the installed public KiCad Python binding's plugin search routine located the isolated profile path; none of that implementation was copied into this project.
