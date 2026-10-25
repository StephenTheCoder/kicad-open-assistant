"""Actual PCB dock. The GUI process imports only stdlib, wx and our core policy."""
import base64
from io import BytesIO
import json
from pathlib import Path
import sys
import threading
import uuid
import wx
import wx.aui
import wx.lib.scrolledpanel
from .policy import AppError, DEFAULT_MODEL, INSTRUCTIONS, make_request
from .process import Task

TESTED_VERSION = "10.0.7"


def message_text(message):
    return "\n".join(p.get("text", "[Reviewed image]") for p in message["content"])


class ConnectionDialog(wx.Dialog):
    def __init__(self, parent, settings):
        super().__init__(parent, title="Connection settings", size=(650, 530), style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
        box = wx.BoxSizer(wx.VERTICAL)
        grid = wx.FlexGridSizer(2, 10, 10)
        grid.AddGrowableCol(1)
        self.mode = wx.Choice(self, choices=["Personal OpenAI key", "Sponsored access token"])
        self.mode.SetSelection(1 if settings["mode"] == "sponsored" else 0)
        self.model = wx.TextCtrl(self, value=settings["model"])
        self.endpoint = wx.TextCtrl(self, value=settings.get("endpoint", ""))
        self.limit = wx.SpinCtrl(self, min=16, max=4096, initial=settings.get("output_limit", 2048))
        self.secret = wx.TextCtrl(self, style=wx.TE_PASSWORD)
        for label, control in (("Connection &mode", self.mode), ("Responses &model ID", self.model), ("Sponsored HTTPS &address", self.endpoint), ("Maximum &output tokens", self.limit), ("New &key or access token", self.secret)):
            grid.Add(wx.StaticText(self, label=label), 0, wx.ALIGN_CENTER_VERTICAL)
            grid.Add(control, 1, wx.EXPAND)
        box.Add(grid, 0, wx.ALL | wx.EXPAND, 16)
        note = wx.StaticText(self, label="Personal: your OpenAI account pays for API usage.\nSponsored: use a revocable access token issued by the operator; no OpenAI key or subscription is required.\n\nCredentials are stored only in Windows Credential Manager. Leave the secret field empty to keep the saved credential. Never put a key in the address or model field.")
        note.Wrap(600)
        box.Add(note, 0, wx.ALL, 16)
        self.forget = wx.CheckBox(self, label="&Remove saved credential for this connection")
        box.Add(self.forget, 0, wx.ALL, 16)
        box.Add(self.CreateButtonSizer(wx.OK | wx.CANCEL), 0, wx.ALL | wx.ALIGN_RIGHT, 16)
        self.SetSizer(box)
        self.SetMinSize((610, 500))

    def values(self):
        return {"mode": "sponsored" if self.mode.GetSelection() else "personal", "model": self.model.GetValue().strip(), "endpoint": self.endpoint.GetValue().strip(), "output_limit": self.limit.GetValue()}


class ReviewDialog(wx.Dialog):
    def __init__(self, parent, request, settings, omitted):
        super().__init__(parent, title="Review exactly what will leave this computer", size=(800, 650), style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
        box = wx.BoxSizer(wx.VERTICAL)
        notebook = wx.Notebook(self)
        # Redact image encoding only in the text tab; every actual image has its own tab.
        text_copy = json.loads(json.dumps(request))
        images = []
        for message in text_copy["input"]:
            for part in message["content"]:
                if part["type"] == "input_image":
                    images.append(part["image_url"])
                    part["image_url"] = f"[Actual outgoing image shown in Image {len(images)} tab]"
        destination = "https://api.openai.com/v1/responses" if settings["mode"] == "personal" else settings["endpoint"].rstrip("/") + "/v1/chat → OpenAI"
        intro = f"Destination: {destination}\nMode: {settings['mode']}\nModel: {request['model']}\nEncoded request: {len(json.dumps(request).encode())} bytes\nEarlier messages omitted by your history selection: {omitted}\n\nFixed advisory instructions:\n{INSTRUCTIONS}\n\nOutgoing conversation, context and attachments:\n"
        text = wx.TextCtrl(notebook, value=intro + json.dumps(text_copy, ensure_ascii=False, indent=2), style=wx.TE_MULTILINE | wx.TE_READONLY | wx.HSCROLL)
        text.SetName("Complete outgoing text preview")
        notebook.AddPage(text, "Text and destination")
        for index, url in enumerate(images, 1):
            page = wx.ScrolledWindow(notebook)
            page.SetScrollRate(20, 20)
            layout = wx.BoxSizer(wx.VERTICAL)
            image = wx.Image(BytesIO(base64.b64decode(url.split(",", 1)[1])), wx.BITMAP_TYPE_PNG)
            layout.Add(wx.StaticText(page, label=f"Actual outgoing PNG: {image.GetWidth()} × {image.GetHeight()} pixels; model detail: low."), 0, wx.ALL, 10)
            layout.Add(wx.StaticBitmap(page, bitmap=wx.Bitmap(image)), 0, wx.ALL, 10)
            page.SetSizer(layout)
            notebook.AddPage(page, f"Image {index}")
        box.Add(notebook, 1, wx.ALL | wx.EXPAND, 12)
        note = wx.StaticText(self, label="Cancel to edit or remove content. Sending shares this snapshot with the named destination and OpenAI. Local history stays on this computer; provider retention policies still apply.")
        note.Wrap(740)
        box.Add(note, 0, wx.ALL, 12)
        buttons = self.CreateButtonSizer(wx.OK | wx.CANCEL)
        self.FindWindowById(wx.ID_OK).SetLabel("&Send reviewed snapshot")
        box.Add(buttons, 0, wx.ALL | wx.ALIGN_RIGHT, 12)
        self.SetSizer(box)
        self.SetMinSize((640, 480))


class AssistantPanel(wx.lib.scrolledpanel.ScrolledPanel):
    def __init__(self, host, pcbnew, close_callback, python=None):
        super().__init__(host)
        self.pcbnew, self.close_callback = pcbnew, close_callback
        self.python = Path(python or (Path(sys.base_prefix) / "python.exe"))
        self.alive, self.loading = True, False
        self.load_generation = 0
        self.tasks, self.chat_task, self.load_task = [], None, None
        self.selected, self.messages, self.conversations = None, [], []
        self.omitted = 0
        self.attachments, self.context, self.drafts = [], "", {}
        self.active, self.answer, self.reply_id, self.request_id = None, "", None, None
        self.settings = {"mode": "personal", "model": DEFAULT_MODEL, "endpoint": "", "output_limit": 2048, "history_count": 8}
        layout = wx.BoxSizer(wx.VERTICAL)
        title = wx.StaticText(self, label="KiCad Open Assistant · experimental PCB dock")
        title.SetFont(title.GetFont().Bold())
        layout.Add(title, 0, wx.ALL, 10)
        self.choice = wx.Choice(self)
        self.choice.SetName("Conversation")
        self.choice.Bind(wx.EVT_CHOICE, self.switch)
        layout.Add(self.choice, 0, wx.LEFT | wx.RIGHT | wx.EXPAND, 10)
        row = wx.BoxSizer(wx.HORIZONTAL)
        for label, handler in (("&New", self.new), ("&Rename", self.rename), ("&Delete", self.delete), ("E&xport", self.export)):
            button = wx.Button(self, label=label)
            button.Bind(wx.EVT_BUTTON, handler)
            row.Add(button, 1, wx.RIGHT, 4)
        layout.Add(row, 0, wx.ALL | wx.EXPAND, 10)
        self.transcript = wx.TextCtrl(self, style=wx.TE_MULTILINE | wx.TE_READONLY)
        self.transcript.SetName("Conversation transcript")
        self.transcript.SetMinSize((-1, 110))
        layout.Add(self.transcript, 1, wx.LEFT | wx.RIGHT | wx.EXPAND, 10)
        self.files = wx.ListBox(self, size=(-1, 64))
        self.files.SetName("Selected attachments")
        layout.Add(self.files, 0, wx.ALL | wx.EXPAND, 10)
        row = wx.BoxSizer(wx.HORIZONTAL)
        for label, handler in (("&Attach", self.attach), ("&Inspect / edit", self.inspect_attachment), ("Remo&ve", self.remove_attachment)):
            button = wx.Button(self, label=label)
            button.Bind(wx.EVT_BUTTON, handler)
            row.Add(button, 1, wx.RIGHT, 4)
        layout.Add(row, 0, wx.LEFT | wx.RIGHT | wx.EXPAND, 10)
        self.board = wx.CheckBox(self, label="Include explicitly selected active &board summary")
        layout.Add(self.board, 0, wx.ALL, 10)
        row = wx.BoxSizer(wx.HORIZONTAL)
        row.Add(wx.StaticText(self, label="Previous &messages to include:"), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 8)
        self.history = wx.SpinCtrl(self, min=0, max=40, initial=8)
        row.Add(self.history, 0)
        layout.Add(row, 0, wx.LEFT | wx.RIGHT, 10)
        layout.Add(wx.StaticText(self, label="&Message (Ctrl+Enter reviews; Escape cancels)"), 0, wx.ALL, 10)
        self.prompt = wx.TextCtrl(self, style=wx.TE_MULTILINE, size=(-1, 70))
        self.prompt.SetName("Message")
        self.prompt.Bind(wx.EVT_KEY_DOWN, self.key)
        layout.Add(self.prompt, 0, wx.LEFT | wx.RIGHT | wx.EXPAND, 10)
        row = wx.BoxSizer(wx.HORIZONTAL)
        self.send = wx.Button(self, label="Re&view and send")
        self.send.Bind(wx.EVT_BUTTON, self.review)
        row.Add(self.send, 1, wx.RIGHT, 4)
        self.cancel_button = wx.Button(self, label="&Cancel")
        self.cancel_button.Bind(wx.EVT_BUTTON, self.cancel)
        row.Add(self.cancel_button, 0)
        layout.Add(row, 0, wx.ALL | wx.EXPAND, 10)
        row = wx.BoxSizer(wx.HORIZONTAL)
        for label, handler in (("C&onnection", self.connection), ("Check &allowance", self.allowance), ("&Hide", lambda e: self.close_callback())):
            button = wx.Button(self, label=label)
            button.Bind(wx.EVT_BUTTON, handler)
            row.Add(button, 1, wx.RIGHT, 4)
        layout.Add(row, 0, wx.LEFT | wx.RIGHT | wx.EXPAND, 10)
        self.status = wx.TextCtrl(self, value="Loading local conversations…", style=wx.TE_READONLY | wx.TE_MULTILINE | wx.BORDER_NONE, size=(-1, 45))
        self.status.SetName("Request status")
        layout.Add(self.status, 0, wx.ALL | wx.EXPAND, 10)
        self.SetSizer(layout)
        self.SetupScrolling(scroll_x=False)
        self.Bind(wx.EVT_WINDOW_DESTROY, self.on_destroy)
        self.reload(recover=True)

    def info(self, text):
        if self.alive:
            self.status.ChangeValue(text)

    def operation(self, command, handler, timeout=30):
        self.tasks = [task for task in self.tasks if task.thread.is_alive()]
        def deliver(event):
            if self.alive:
                wx.CallAfter(self.received, handler, event, task)
        task = Task(self.python, command, deliver, timeout)
        self.tasks.append(task)
        task.start()
        return task

    def received(self, handler, event, task):
        if not self.alive or task.cancelled.is_set():
            return
        if event["type"] == "error":
            self.info(event["message"])
        handler(event)

    def reload(self, identifier=None, recover=False, status=None):
        if self.load_task:
            self.load_task.cancel()
        self.loading = True
        self.load_generation += 1
        generation = self.load_generation
        self.choice.Disable()
        def done(event):
            if generation != self.load_generation:
                return
            if event["type"] == "result":
                value = event["value"]
                self.conversations, self.messages, self.selected = value["conversations"], value["messages"], value["selected"]
                self.omitted = value["omitted"]
                self.settings.update(value["settings"])
                self.choice.Set([r["title"] for r in self.conversations])
                self.choice.SetSelection(next(i for i, r in enumerate(self.conversations) if r["id"] == self.selected))
                self.render()
                self.info(status or f"{self.settings['mode']} · {self.settings['model']} · No content sent until reviewed.")
            if event["type"] in {"exit", "error"}:
                self.loading = False
                self.choice.Enable()
        self.load_task = self.operation({"action": "load", "conversation": identifier, "recover": recover}, done)

    def render(self):
        visible = [m for m in self.messages if not (self.active == self.selected and m["role"] == "assistant" and m["status"] == "streaming")]
        text = "\n\n".join(f"{m['role'].title()} [{m['status']}]:\n{message_text(m)}" for m in visible)
        if self.omitted:
            text = f"{self.omitted} earlier messages remain saved locally. Export includes the complete conversation; this view loads at most 40 messages / 30 MiB.\n\n" + text
        if self.active == self.selected:
            text += "\n\nAssistant [streaming]:\n" + self.answer
        self.transcript.ChangeValue(text or "Ask an electronics or KiCad question. This assistant cannot modify designs.")
        self.transcript.ShowPosition(self.transcript.GetLastPosition())

    def switch(self, event):
        if self.loading:
            return
        self.drafts[self.selected] = self.prompt.GetValue()
        identifier = self.conversations[self.choice.GetSelection()]["id"]
        self.prompt.ChangeValue(self.drafts.get(identifier, ""))
        self.attachments.clear()
        self.files.Clear()
        self.board.SetValue(False)
        self.reload(identifier)

    def new(self, event):
        self.operation({"action": "create"}, lambda e: self.reload(e["value"]) if e["type"] == "result" else None)
        self.prompt.ChangeValue("")
        self.attachments.clear()
        self.files.Clear()
        self.board.SetValue(False)

    def rename(self, event):
        if not self.selected:
            return
        with wx.TextEntryDialog(self, "Conversation name", "Rename conversation", self.choice.GetStringSelection()) as dialog:
            if dialog.ShowModal() == wx.ID_OK and dialog.GetValue().strip():
                self.operation({"action": "rename", "conversation": self.selected, "title": dialog.GetValue()}, lambda e: self.reload(self.selected) if e["type"] == "result" else None)

    def delete(self, event):
        if not self.selected:
            return
        if wx.MessageBox("Delete this local conversation and its stored attachment snapshots? Provider retention is separate.", "Delete conversation", wx.YES_NO | wx.NO_DEFAULT | wx.ICON_QUESTION, self) != wx.YES:
            return
        identifier = self.selected
        if self.active == identifier:
            self.cancel(None)
        self.operation({"action": "delete", "conversation": identifier}, lambda e: self.reload() if e["type"] == "result" else None)

    def export(self, event):
        if not self.selected:
            return
        with wx.FileDialog(self, "Export local conversation", wildcard="JSON (*.json)|*.json", style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT) as dialog:
            if dialog.ShowModal() == wx.ID_OK:
                self.operation({"action": "export", "conversation": self.selected, "path": dialog.GetPath()}, lambda e: self.info("Complete persisted conversation exported locally, including stored attachment snapshots.") if e["type"] == "result" else None)

    def attach(self, event):
        if len(self.attachments) >= 8:
            self.info("Maximum 8 attachments per message.")
            return
        with wx.FileDialog(self, "Select one attachment", style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST) as dialog:
            if dialog.ShowModal() != wx.ID_OK:
                return
            path = dialog.GetPath()
        self.info("Extracting selected file locally…")
        selected = self.selected
        def done(event):
            if event["type"] == "result" and self.selected == selected:
                item = event["value"]
                if len(self.attachments) >= 8 or sum(a["original_bytes"] for a in self.attachments) + item["original_bytes"] > 20 * 1024 * 1024:
                    self.info("Attachment total exceeds 8 files or 20 MiB.")
                    return
                self.attachments.append(item)
                self.files.Append(item["name"])
                self.info(item.get("warning", "Local snapshot ready. Review before sending."))
        self.operation({"action": "extract", "path": path}, done)

    def inspect_attachment(self, event):
        index = self.files.GetSelection()
        if index == wx.NOT_FOUND:
            self.info("Select an attachment to inspect.")
            return
        item = self.attachments[index]
        if item.get("image_url"):
            request = make_request(self.settings["model"], "Image inspection only", [], [item])
            with ReviewDialog(self, request, self.settings, 0) as dialog:
                dialog.FindWindowById(wx.ID_OK).Hide()
                dialog.ShowModal()
        else:
            with wx.TextEntryDialog(self, "Edit outgoing text only; original file is unchanged.", item["name"], item["text"], style=wx.OK | wx.CANCEL | wx.TE_MULTILINE | wx.RESIZE_BORDER) as dialog:
                dialog.SetSize((700, 550))
                if dialog.ShowModal() == wx.ID_OK:
                    item["text"] = dialog.GetValue()

    def remove_attachment(self, event):
        index = self.files.GetSelection()
        if index != wx.NOT_FOUND:
            self.attachments.pop(index)
            self.files.Delete(index)

    def connection(self, event):
        with ConnectionDialog(self, self.settings) as dialog:
            if dialog.ShowModal() != wx.ID_OK:
                return
            settings = dialog.values()
            command = {"action": "settings", "settings": settings, "credential": dialog.secret.GetValue(), "forget": dialog.forget.GetValue()}
            dialog.secret.ChangeValue("")
        def done(event):
            if event["type"] == "result":
                self.settings.update(settings)
                self.info("Connection saved. Credentials are held in Windows Credential Manager.")
        self.operation(command, done)

    def allowance(self, event):
        if self.settings["mode"] != "sponsored":
            self.info("Personal mode uses your OpenAI account; this app cannot read its billing balance.")
            return
        def done(event):
            if event["type"] == "result":
                value = event["value"]
                self.info(f"Sponsored {'enabled' if value['enabled'] else 'disabled'}; allowance remaining ${value['remaining_microdollars'] / 1_000_000:.4f}. Model {value['model']}, output cap {value['max_output_tokens']}. Set these in Connection before review.")
        self.operation({"action": "status", "settings": self.settings.copy()}, done)

    def review(self, event):
        if self.chat_task or self.loading or not self.selected:
            self.info("Wait for the current operation or cancel it before sending.")
            return
        context = ""
        if self.board.GetValue():
            board = self.pcbnew.GetBoard()
            if board is None:
                self.info("No active board available. Clear board context or open a board.")
                return
            context = json.dumps({"file": Path(board.GetFileName()).name or "Unsaved board", "snapshot": "live editor metadata, including unsaved changes; not raw design", "footprints": len(board.GetFootprints()), "track_segments": len(board.GetTracks()), "nets": board.GetNetCount()}, indent=2)
        available = [{"role": m["role"], "content": m["content"]} for m in self.messages if m["status"] == "completed"]
        count = self.history.GetValue()
        history = available[-count:] if count else []
        try:
            request = make_request(self.settings["model"], self.prompt.GetValue(), history, self.attachments, context, self.settings["output_limit"])
        except AppError as error:
            self.info(error.message)
            return
        settings = self.settings.copy()
        with ReviewDialog(self, request, settings, self.omitted + len(available) - len(history)) as dialog:
            if dialog.ShowModal() != wx.ID_OK:
                return
        self.active, self.answer, self.reply_id, self.request_id = self.selected, "", None, uuid.uuid4().hex
        request_id = self.request_id
        result_status = ["Connecting…"]
        self.info("Connecting… Cancel closes the local worker and stream. Already processed tokens may be billed.")
        self.send.Disable()
        def update(event):
            if request_id != self.request_id:
                return
            if event["type"] == "started":
                self.reply_id = event["reply_id"]
                if self.active == self.selected and not any(m.get("id") == event["user_id"] for m in self.messages):
                    self.messages.append({"id": event["user_id"], "role": "user", "content": request["input"][-1]["content"], "status": "completed"})
            elif event["type"] == "delta":
                self.answer += event["text"]
                self.render()
            elif event["type"] == "done":
                result_status[0] = "Response " + event["status"] + ". Usage: " + json.dumps(event.get("usage"))
                self.info(result_status[0])
            elif event["type"] == "error":
                result_status[0] = event["message"]
            elif event["type"] == "exit":
                completed_conversation = self.active
                self.active, self.chat_task = None, None
                self.send.Enable()
                if self.selected == completed_conversation:
                    self.reload(self.selected, status=result_status[0])
        self.chat_task = self.operation({"action": "chat", "conversation": self.active, "request": request, "settings": settings, "request_id": request_id}, update, 190)

    def cancel(self, event):
        cancelled_status = "Cancelled locally. Already processed tokens may still be billed. Sponsored unknown usage retains its budget reservation."
        for task in self.tasks:
            if task is not self.chat_task and task.thread.is_alive():
                task.cancel()
        if self.chat_task:
            stopped_task = self.chat_task
            stopped_task.cancel()
            conversation, reply, answer = self.active, self.reply_id, self.answer
            self.request_id = None
            self.active, self.chat_task = None, None
            def finalize():
                if not self.alive:
                    return
                if reply:
                    self.operation({"action": "finish", "reply_id": reply, "text": answer, "status": "cancelled"}, lambda e: self.reload(conversation, status=cancelled_status) if e["type"] == "result" and self.selected == conversation else None)
                else:
                    self.operation({"action": "recover", "conversation": conversation}, lambda e: self.reload(self.selected, status=cancelled_status) if e["type"] == "result" else None)
            def after_stop():
                stopped_task.thread.join()
                wx.CallAfter(finalize)
            threading.Thread(target=after_stop, daemon=True).start()
        self.loading = False
        self.load_generation += 1
        self.choice.Enable()
        self.send.Enable()
        self.info(cancelled_status)

    def key(self, event):
        if event.ControlDown() and event.GetKeyCode() in (wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER):
            self.review(None)
        elif event.GetKeyCode() == wx.WXK_ESCAPE:
            self.cancel(None)
        else:
            event.Skip()

    def on_destroy(self, event):
        if event.GetEventObject() is self:
            self.alive = False
            for task in self.tasks:
                task.cancel()
        event.Skip()


def register(pcbnew):
    class OpenAssistantAction(pcbnew.ActionPlugin):
        def defaults(self):
            self.name = "KiCad Open Assistant"
            self.category = "Advisory assistant"
            self.description = "Experimental PCB-only dock for KiCad 10.0.7"
            self.show_toolbar_button = True
            self.panel = None

        def Run(self):
            if sys.platform != "win32" or pcbnew.Version() != TESTED_VERSION:
                wx.MessageBox("This experimental release is validated only on Windows KiCad 10.0.7. No alternate window will be opened.", "Unsupported KiCad version", wx.OK | wx.ICON_INFORMATION)
                return
            hosts = [w for w in wx.GetTopLevelWindows() if isinstance(w, wx.Frame) and w.GetName() == "PcbFrame"]
            if len(hosts) != 1:
                wx.MessageBox("Could not identify exactly one PCB editor instance.", "KiCad Open Assistant")
                return
            host = hosts[0]
            manager = wx.aui.AuiManager.GetManager(host)
            if manager is None:
                wx.MessageBox("KiCad's docking manager is unavailable in this build.", "KiCad Open Assistant")
                return
            if self.panel:
                manager.GetPane(self.panel).Show()
                manager.Update()
                if not self.panel.selected:
                    self.panel.reload()
                self.panel.prompt.SetFocus()
                return
            def hide():
                self.panel.cancel(None)
                manager.GetPane(self.panel).Hide()
                manager.Update()
            self.panel = AssistantPanel(host, pcbnew, hide)
            pane = wx.aui.AuiPaneInfo().Name("kicad_open_assistant").Caption("KiCad Open Assistant · experimental").Right().Layer(1).BestSize(540, 800).MinSize(440, 400).CloseButton(False).Floatable(False)
            if not manager.AddPane(self.panel, pane):
                self.panel.Destroy()
                self.panel = None
                wx.MessageBox("KiCad refused the dock. No external window was substituted.", "KiCad Open Assistant")
                return
            manager.Update()
    OpenAssistantAction().register()
