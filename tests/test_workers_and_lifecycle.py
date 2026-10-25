import asyncio
import json
import os
from pathlib import Path
import sys
import threading
import time
from types import SimpleNamespace
import pytest
from kicad_open_assistant.attachments import extract
from kicad_open_assistant.policy import make_request
from kicad_open_assistant.process import Task
from kicad_open_assistant.transport import openai_stream


def text_pdf(path):
    from pypdf import PdfWriter
    from pypdf.generic import DictionaryObject, NameObject, DecodedStreamObject
    writer = PdfWriter()
    page = writer.add_blank_page(width=300, height=200)
    font = DictionaryObject({NameObject('/Type'): NameObject('/Font'), NameObject('/Subtype'): NameObject('/Type1'), NameObject('/BaseFont'): NameObject('/Helvetica')})
    page[NameObject('/Resources')] = DictionaryObject({NameObject('/Font'): DictionaryObject({NameObject('/F1'): writer._add_object(font)})})
    stream = DecodedStreamObject()
    stream.set_data(b'BT /F1 12 Tf 20 150 Td (Original resistor reference: 1000 ohms.) Tj ET')
    page[NameObject('/Contents')] = writer._add_object(stream)
    writer.write(path)


def test_pdf_text_and_limit(tmp_path):
    path = tmp_path / 'reference.pdf'
    text_pdf(path)
    assert '1000 ohms' in extract(path)['text']
    from pypdf import PdfWriter
    writer = PdfWriter()
    for _ in range(101):
        writer.add_blank_page(width=10, height=10)
    writer.write(path)
    with pytest.raises(Exception, match='100 pages'):
        extract(path)


def test_real_disposable_worker_and_persistence(tmp_path, monkeypatch):
    monkeypatch.setenv('KOA_DATA_HOME', str(tmp_path / 'state'))
    events, done = [], threading.Event()
    def callback(event):
        events.append(event)
        if event['type'] == 'exit':
            done.set()
    task = Task(sys.executable, {'action': 'load', 'recover': True}, callback, timeout=10).start()
    assert done.wait(15)
    task.thread.join(3)
    results = [e for e in events if e['type'] == 'result']
    assert results, events
    first_id = results[0]['value']['selected']
    events.clear()
    done.clear()
    task = Task(sys.executable, {'action': 'load'}, callback, timeout=10).start()
    assert done.wait(15)
    assert next(e for e in events if e['type'] == 'result')['value']['selected'] == first_id


@pytest.mark.asyncio
async def test_async_cancellation_closes_stream():
    closed = asyncio.Event()
    started = asyncio.Event()
    class WaitingStream:
        async def __aenter__(self):
            return self
        async def __aexit__(self, *args):
            closed.set()
        def __aiter__(self):
            return self.generate()
        async def generate(self):
            started.set()
            await asyncio.sleep(100)
            yield
    async def create(**kwargs):
        return WaitingStream()
    async def consume():
        async for _ in openai_stream(make_request('gpt-4.1-mini', 'Hello', [], []), 'synthetic', SimpleNamespace(responses=SimpleNamespace(create=create))):
            pass
    task = asyncio.create_task(consume())
    await asyncio.wait_for(started.wait(), 1)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert closed.is_set()
