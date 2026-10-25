# Licensing and distribution

Original code and original prose in this repository are offered under **MIT**, with the license text at the root. MIT is suitable for free distribution, reuse and contributions; it permits downstream commercial use too. If reciprocal source sharing is preferred later, GPL-3.0-or-later is a reasonable alternative before external contributions. The current choice is MIT for the independently authored files, not a relicensing of KiCad or any dependency.

## Dependencies and release obligations

| Component | Role/status | Public license source | Release action |
|---|---|---|---|
| KiCad 10.0.7 / pcbnew | Installed host; not bundled | [KiCad licenses](https://www.kicad.org/about/licenses/): primarily GPL-3.0-or-later | Preserve the host's terms; any distributed KiCad fork needs corresponding source, notices and GPL compliance |
| Python 3.11.5 | Host interpreter; not bundled | [Python license](https://docs.python.org/3/license.html) | Include applicable PSF and bundled dependency notices if distributing a runtime |
| wxPython 4.3.1 / wxWidgets 3.3.3 | Installed host UI; not bundled | [wxWindows Library Licence](https://wxpython.org/pages/license/index.html) | Preserve license/exception and bundled notices if packaging it |
| OpenAI Python SDK 3.37.0 | Bundled worker dependency | [Apache-2.0](https://github.com/openai/openai-python/blob/main/LICENSE) | Hash-pinned; distribution license retained |
| pypdf 6.21.2 | Bundled local PDF extraction | [BSD-3-Clause](https://github.com/py-pdf/pypdf/blob/main/LICENSE) | Exact distribution's three conditions, copyright and disclaimer retained |
| python-docx 1.2.0 | Bundled DOCX extraction | [MIT](https://github.com/python-openxml/python-docx/blob/master/LICENSE) | Notices retained, including lxml's bundled native licenses |
| Pillow 13.0.0 | Bundled image validation/metadata removal | MIT-CMU; exact wheel notices | Native library notices retained |
| OS credential-store adapter | Original ctypes Windows API adapter | MIT original source | No third-party adapter bundled; no file fallback |
| Official kicad-python IPC client | Not used in the accepted architecture | Not bundled | No dependency or license claim for this release |

No proprietary plugin content is licensed by this repository. Test screenshots show KiCad UI and our prototype; KiCad names/interface elements remain their owners' material. Do not present this working name as official KiCad branding. No third-party logos or copied visual assets are included.

The client archive includes the hash-locked dependencies, `dependencies.json` license inventory, a CycloneDX 1.6 component SBOM (`sbom.cdx.json`), and original distribution license directories including native-library notices. See THIRD-PARTY-NOTICES.md. The SBOM lists packaged Python distributions; nested native components are documented by their wheel license files. The host Python/wx/KiCad binaries are not bundled. Service dependencies are separately locked and installed with their notices into the backend image.

MIT original code can be incorporated into a GPL-covered combined distribution while retaining its notice. Whether a particular plugin/bundle arrangement forms a combined work is a distribution question to resolve before packaging; this document does not claim that a KiCad-linked or forked binary can be distributed solely under MIT. A maintained KiCad fork is the largest licensing/maintenance change among the UI choices.
