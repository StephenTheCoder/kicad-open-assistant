# ADR 001: UI hosting requires a product choice

Status: **accepted, option A**, 2026-10-24. The owner explicitly selected an experimental PCB-only dock pinned to tested KiCad 10. The initial release is gated to Windows KiCad 10.0.7 with its bundled Python/wx runtime; broader versions require separate validation. Schematic documents may be attached, but schematic UI hosting is not included.

## Finding

A real PCB dock is possible on this installation without a KiCad fork. Our original ActionPlugin obtains the editor's existing wx AUI manager and adds a child panel. Both the visible layout and runtime `IsDocked()` check establish actual docking. This uses internal UI access through the legacy embedded Python interpreter; it is not an advertised, stable KiCad panel extension API.

A separate `wx.Frame` parented to the PCB editor also works. It is a **KiCad-owned modeless window**, in the editor process, with editor ownership, but is still floating. It must never be marketed as a docked or embedded panel. Both probes use the same deprecated interpreter, so choosing modeless alone does not remove that dependency.

The supported IPC architecture launches an external process. It provides no documented facility for inserting that process's widgets into KiCad's layout. Our action launched from both PCB and schematic editors on this installed build, with instance socket/token variables present. The external wx window did not become targetable in this run; process launch is verified, companion GUI completion and API data exchange are not. No browser was substituted. See [actual evidence and limits](FEASIBILITY.md).

## PCB and schematic are different capabilities

| Capability | PCB 10.0.7 | Schematic 10.0.7 |
|---|---|---|
| Legacy ActionPlugin entry point | Ran successfully | No equivalent entry point found; official Python bindings are PCB-only |
| KiCad-owned modeless window | Demonstrated | Not demonstrated / no supported host hook found |
| True dock in editor layout | Demonstrated via internal AUI manager | Not demonstrated / no supported panel hook found |
| IPC action registration and process launch | Demonstrated | **Demonstrated**, despite documentation's version boundary |
| Read design through IPC | Not tested | Not tested; launch alone does not establish schematic API coverage |

Official [legacy binding documentation](https://dev-docs.kicad.org/en/apis-and-binding/pcbnew/) says SWIG bindings are deprecated since KiCad 9, unstable across major releases, and planned for removal in 11. Official [IPC documentation](https://dev-docs.kicad.org/en/apis-and-binding/ipc-api/for-addon-developers/) assigns schematic plugins to 11 while this local 10.0.7 build exposes an action launcher. Treat that as a runtime/documentation discrepancy, not a general compatibility promise. KiCad 11 has not been installed or tested here.

## Options to approve

| Option | Meets inside-editor requirement? | Cost and practical limits |
|---|---|---|
| A. Experimental PCB dock, pinned to tested KiCad 10 | Yes, PCB only | Internal AUI ownership/layout/lifetime risks; regression tests for every supported KiCad/wx build; removal of SWIG requires replacement or retained old host. Schematic UI remains unavailable |
| B. KiCad-owned modeless PCB window | Owned by KiCad, but not docked | Avoids AUI pane internals; still legacy Python and PCB-only. Lower short-term UI risk, no durable solution to removal of SWIG |
| C. Native IPC companion | No; explicit relaxation of requirement | Best supported extension boundary; independent GUI and dependency packaging, instance/capability detection, and completion of the visible-window test still needed. Launch from both editors observed; schematic data support remains a separate gate |
| D. Upstream panel extension or maintained KiCad fork | Can target both editors | No full prototype yet. Requires C++/wx lifecycle design, upstream acceptance or ongoing rebases, platform builds, signed installers, security/update work and GPL distribution obligations. Largest continuing maintenance commitment |

Recommendation: choose **C** if a supported, freely distributed assistant is the priority and a separate native window is acceptable. If staying inside KiCad is mandatory, choose **A only as a clearly experimental PCB-only release**, or commission **D** for a durable product in both editors. B is the nearest demonstrated alternative to docking inside KiCad's process, but is not a long-term maintenance escape.

No cross-process window reparenting, memory patching, private pointer coercion or hidden browser is proposed. The owner chose A after reviewing these limitations. These are qualitative maintenance estimates, not quoted delivery schedules.

## Consequence for the scaffold

Keep host-independent conversation/payload/transport logic separate from the KiCad UI adapter. Preserve explicit context review and no automatic board mutation. Implement the real dock with a version gate; do not silently fall back to a floating window. The historical feasibility milestone is complete; the basic-release Goal is now authorized.
