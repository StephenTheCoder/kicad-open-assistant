# Third-party notices

Original application code and documentation are MIT licensed. Bundled dependencies retain their own licenses. The release contains each dependency's distribution metadata and license files under `plugins/vendor`, plus a generated `dependencies.json` inventory. Python and wxPython are supplied by the existing KiCad installation, not redistributed here.

Direct dependencies: OpenAI Python SDK (Apache-2.0), httpx (BSD-3-Clause), pypdf 6.21.2 (BSD-3-Clause, verified in this distribution's LICENSE), defusedxml (PSF), and Pillow (MIT-CMU). Transitive components include native pydantic-core and jiter, certifi (MPL-2.0), typing-extensions (PSF-2.0), and other certificate/runtime packages. Consult the bundled license files and generated inventory for the exact pinned distributions; this short list does not replace their notices. The certifi certificate bundle is distributed unmodified with its source and MPL notice. python-docx/lxml are development-only and are not bundled.

Pillow's complete native-component notices are retained in its distribution LICENSE. Portions of this software use the FreeType Project (https://freetype.org), under the FreeType License. All rights reserved. This software is based in part on the work of the Independent JPEG Group. These credits supplement the full bundled FreeType, JPEG, PNG, TIFF, WebP, compression and other component terms.

KiCad is a separate GPL-covered host. This project is not endorsed by KiCad or OpenAI and contains no KiCad logos, proprietary plugin source, branding or evidence archive. MIT original code is GPL-compatible; distributing a KiCad fork would require its own corresponding-source and notice obligations.
