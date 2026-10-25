"""Original, offline IPC action launch probe; explicitly a separate process.
SPDX-License-Identifier: MIT
"""
import json
import os
import wx

event = {
    "event": "ipc_action_launched",
    "pid": os.getpid(),
    "parent_pid": os.getppid(),
    "api_socket_present": bool(os.environ.get("KICAD_API_SOCKET")),
    "api_token_present": bool(os.environ.get("KICAD_API_TOKEN")),
    "classification": "separate companion process; not embedded",
}
log = os.environ.get("KOA_PROBE_LOG")
if log:
    with open(log, "a", encoding="utf-8") as handle:
        handle.write(json.dumps(event) + "\n")
app = wx.App()
window = wx.Frame(None, title="KiCad Open Assistant - IPC companion probe", size=(690, 410))
panel = wx.Panel(window)
layout = wx.BoxSizer(wx.VERTICAL)
layout.Add(wx.StaticText(panel, label="Separate companion process — NOT embedded in KiCad"), 0, wx.ALL, 16)
layout.Add(wx.TextCtrl(panel, value="No board data or model requests are used.\n" + json.dumps(event, indent=2), style=wx.TE_MULTILINE | wx.TE_READONLY), 1, wx.EXPAND | wx.ALL, 16)
close = wx.Button(panel, label="&Close")
close.Bind(wx.EVT_BUTTON, lambda event: window.Close())
layout.Add(close, 0, wx.ALL, 16)
panel.SetSizer(layout)
window.Show()
app.MainLoop()
