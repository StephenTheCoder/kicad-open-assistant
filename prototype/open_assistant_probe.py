"""Original KiCad UI feasibility probe. Local demo only; no network client.

SPDX-License-Identifier: MIT
The legacy adapter is intentionally isolated from the proposed product core.
"""
import json
import os
from pathlib import Path
import platform
import time

import pcbnew
import wx
import wx.aui


def record(event, **fields):
    destination = os.environ.get("KOA_PROBE_LOG")
    if destination:
        entry = dict(event=event, time=time.time(), pid=os.getpid(), **fields)
        with open(destination, "a", encoding="utf-8") as stream:
            stream.write(json.dumps(entry) + "\n")


class DemoPanel(wx.Panel):
    def __init__(self, parent, host_kind):
        super().__init__(parent)
        self.host_kind = host_kind
        self.timer = wx.Timer(self)
        self.pending = []
        self.previewed = False
        layout = wx.BoxSizer(wx.VERTICAL)
        heading = wx.StaticText(self, label="KiCad Open Assistant | UI feasibility")
        heading.SetFont(heading.GetFont().Bold())
        layout.Add(heading, 0, wx.ALL, 12)
        layout.Add(wx.StaticText(self, label=host_kind + " — local demo, no AI or network"), 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 12)
        self.transcript = wx.TextCtrl(self, value="Choose a context preview, then try the local streaming demo.\n", style=wx.TE_MULTILINE | wx.TE_READONLY)
        self.transcript.SetMinSize((-1, 150))
        self.transcript.SetName("Conversation transcript")
        layout.Add(self.transcript, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 12)
        layout.Add(wx.StaticText(self, label="&Message (Ctrl+Enter to run demo)"), 0, wx.ALL, 12)
        self.prompt = wx.TextCtrl(self, value="What context would you use to explain this board?", style=wx.TE_MULTILINE)
        self.prompt.SetName("Message")
        self.prompt.SetMinSize((-1, 65))
        layout.Add(self.prompt, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 12)
        buttons = wx.BoxSizer(wx.HORIZONTAL)
        for label, handler in (("&Preview board context", self.preview), ("&Run local demo", self.run_demo), ("&Cancel", self.cancel)):
            button = wx.Button(self, label=label)
            button.Bind(wx.EVT_BUTTON, handler)
            buttons.Add(button, 0, wx.RIGHT, 6)
        layout.Add(buttons, 0, wx.ALL, 12)
        self.status = wx.StaticText(self, label="No context selected. Nothing leaves this computer.")
        layout.Add(self.status, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 12)
        self.SetSizer(layout)
        self.Bind(wx.EVT_TIMER, self.tick, self.timer)
        self.Bind(wx.EVT_WINDOW_DESTROY, self.dispose)
        self.prompt.Bind(wx.EVT_KEY_DOWN, self.key)

    def key(self, event):
        if event.ControlDown() and event.GetKeyCode() in (wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER):
            self.run_demo(None)
        elif event.GetKeyCode() == wx.WXK_ESCAPE:
            self.cancel(None)
        else:
            event.Skip()

    def preview(self, event):
        board = pcbnew.GetBoard()
        if board is None:
            self.status.SetLabel("No active PCB. Open a board and try again.")
            return
        # Deliberately bounded and selected by a user action, not automatic upload.
        context = {"board": Path(board.GetFileName()).name or "Unsaved board", "footprints": len(board.GetFootprints()), "tracks": len(board.GetTracks()), "destination": "None — offline prototype"}
        preview = json.dumps(context, indent=2)
        with wx.MessageDialog(self, preview + "\n\nThis is the complete demo context. No file content is read or sent.", "Context preview", wx.OK | wx.CANCEL) as dialog:
            if dialog.ShowModal() == wx.ID_OK:
                self.previewed = True
                self.transcript.AppendText("\nSelected context:\n" + preview + "\n")
                self.status.SetLabel("Context preview accepted locally. No network destination.")
                record("preview_accepted", context=context)

    def run_demo(self, event):
        if self.timer.IsRunning():
            self.status.SetLabel("A demo is running. Cancel it before starting another.")
            return
        if not self.prompt.GetValue().strip():
            self.status.SetLabel("Enter a message first.")
            return
        self.transcript.AppendText("\nYou: " + self.prompt.GetValue() + "\nDemo: ")
        self.pending = list("This is a local UI simulation. The editor stays available while text arrives. No API key is loaded and no model request is sent.")
        self.timer.Start(55)
        self.status.SetLabel("Local demo running — Cancel or Escape stops it.")
        record("demo_started", host_kind=self.host_kind)

    def tick(self, event):
        if self.pending:
            self.transcript.AppendText(self.pending.pop(0))
        else:
            self.timer.Stop()
            self.status.SetLabel("Demo complete. Nothing was sent.")
            record("demo_completed")

    def cancel(self, event):
        was_running = self.timer.IsRunning()
        self.timer.Stop()
        self.pending.clear()
        self.status.SetLabel("Cancelled locally. No network request exists.")
        record("demo_cancelled", was_running=was_running)

    def dispose(self, event):
        if event.GetEventObject() is self:
            self.timer.Stop()
        event.Skip()


class IntegrationProbe(pcbnew.ActionPlugin):
    def defaults(self):
        self.name = "KiCad Open Assistant - UI probe"
        self.category = "UI feasibility"
        self.description = "Original offline prototype: owned window and docking capability probe"
        self.show_toolbar_button = True
        self.window = None
        self.dock_panel = None

    def Run(self):
        if self.window:
            self.window.Raise()
            return
        candidates = [w for w in wx.GetTopLevelWindows() if isinstance(w, wx.Frame) and (w.GetName() == "PcbFrame" or "PCB Editor" in w.GetTitle())]
        if len(candidates) != 1:
            record("host_ambiguous", candidates=[w.GetTitle() for w in candidates])
            wx.MessageBox("Could not identify exactly one PCB editor host.", "UI probe")
            return
        host = candidates[0]
        manager = wx.aui.AuiManager.GetManager(host)
        record("ui_probe", kicad=pcbnew.Version(), python=platform.python_version(), wx=wx.version(), host_class=type(host).__name__, host_name=host.GetName(), host_handle=host.GetHandle(), aui_manager_found=manager is not None, top_level_names=[w.GetName() for w in wx.GetTopLevelWindows()])
        # A returned manager is NOT a supported KiCad extension contract.
        self.manager = manager
        self.host = host
        self.window = wx.Frame(host, title="KiCad Open Assistant - owned modeless prototype", size=(660, 540))
        self.window.SetMinSize((600, 500))
        layout = wx.BoxSizer(wx.VERTICAL)
        layout.Add(DemoPanel(self.window, "KiCad-owned modeless window (not docked)"), 1, wx.EXPAND)
        dock_button = wx.Button(self.window, label="Toggle experimental &docked panel (internal API)")
        dock_button.Enable(manager is not None)
        dock_button.Bind(wx.EVT_BUTTON, self.toggle_dock)
        layout.Add(dock_button, 0, wx.EXPAND | wx.ALL, 8)
        self.window.SetSizer(layout)
        self.window.Bind(wx.EVT_CLOSE, self.close)
        self.window.Show()
        record("modeless_shown", parent_matches=self.window.GetParent() is host, handle=self.window.GetHandle(), parent_handle=host.GetHandle(), is_modal=False)

    def toggle_dock(self, event):
        if self.dock_panel is not None:
            self.manager.DetachPane(self.dock_panel)
            self.dock_panel.Destroy()
            self.dock_panel = None
            self.manager.Update()
            record("experimental_dock_removed")
            return
        self.dock_panel = DemoPanel(self.host, "Experimental dock — unsupported KiCad UI access")
        info = wx.aui.AuiPaneInfo().Name("koa_feasibility_probe").Caption("KiCad Open Assistant | experimental").Right().Layer(1).BestSize(540, 600).MinSize(420, 400).CloseButton(False)
        added = self.manager.AddPane(self.dock_panel, info)
        self.manager.Update()
        pane = self.manager.GetPane(self.dock_panel)
        record("experimental_dock_added", added=bool(added), is_docked=pane.IsDocked(), pane_ok=pane.IsOk(), parent_matches=self.dock_panel.GetParent() is self.host)

    def close(self, event):
        if self.dock_panel is not None:
            self.toggle_dock(None)
        record("modeless_closed")
        self.window.Destroy()
        self.window = None


IntegrationProbe().register()
record("legacy_plugin_registered", kicad=pcbnew.Version())
