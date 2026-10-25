"""Prepare a clearly marked offline-API installation; never overwrite an install.

Run with development dependencies installed. This does not launch or automate UI.
"""
import argparse
import json
from pathlib import Path
import shutil
from install_local import install

ROOT = Path(__file__).resolve().parents[1]

def prepare(archive, profile):
    install(archive, profile)
    package = profile.resolve() / "10.0/scripting/plugins/kicad_open_assistant_plugin/lib/kicad_open_assistant"
    original = package / "worker_entry.py"
    original.rename(package / "_real_worker.py")
    shutil.copyfile(ROOT / "tests/ui_fixture_worker.py", original)
    (package / "fixture-mode.json").write_text(json.dumps({"mode": "stream"}), encoding="utf-8")
    ui = package / "ui.py"
    ui.write_text(ui.read_text(encoding="utf-8").replace("KiCad Open Assistant · experimental PCB dock", "OFFLINE API FIXTURE · actual KiCad dock"), encoding="utf-8")
    fixtures = profile.parent / "attachments"
    fixtures.mkdir(exist_ok=True)
    (fixtures / "notes.txt").write_text("Original UI fixture: a 1 kOhm resistor at 1 mA.\n", encoding="utf-8")
    (fixtures / "board.kicad_pcb").write_text('(kicad_pcb (version 20260101) (generator "original_ui_fixture"))\n', encoding="utf-8")
    from docx import Document
    doc = Document()
    doc.add_paragraph("Original DOCX fixture: resistor notes")
    doc.add_table(1, 2).cell(0, 0).text = "1 kOhm"
    doc.save(fixtures / "notes.docx")
    from PIL import Image, ImageDraw
    im = Image.new("RGB", (500, 160), "white")
    draw = ImageDraw.Draw(im)
    draw.line((30, 80, 180, 80), fill="black", width=3)
    draw.rectangle((180, 55, 310, 105), outline="black", width=3)
    draw.line((310, 80, 460, 80), fill="black", width=3)
    draw.text((220, 25), "1 kOhm", fill="black")
    im.save(fixtures / "resistor.png")
    from pypdf import PdfWriter
    from pypdf.generic import DictionaryObject, NameObject, DecodedStreamObject
    writer = PdfWriter()
    page = writer.add_blank_page(width=300, height=200)
    font = DictionaryObject({NameObject('/Type'): NameObject('/Font'), NameObject('/Subtype'): NameObject('/Type1'), NameObject('/BaseFont'): NameObject('/Helvetica')})
    page[NameObject('/Resources')] = DictionaryObject({NameObject('/Font'): DictionaryObject({NameObject('/F1'): writer._add_object(font)})})
    stream = DecodedStreamObject()
    stream.set_data(b'BT /F1 12 Tf 20 150 Td (Original UI fixture: 1000 ohms.) Tj ET')
    page[NameObject('/Contents')] = writer._add_object(stream)
    writer.write(fixtures / "reference.pdf")
    print("Offline fixtures prepared; no credentials read and no network request made.")
    print("Mode file:", package / "fixture-mode.json")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    parser.add_argument("--profile", type=Path, required=True)
    args = parser.parse_args()
    prepare(args.archive, args.profile)
