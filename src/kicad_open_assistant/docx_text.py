"""Original bounded extraction of DOCX main-body paragraphs and table cells.

No relationship resolution, rendering, macros, XInclude, entities or DTDs.
"""
from io import BytesIO
from defusedxml.ElementTree import iterparse
from .policy import AppError, MAX_TEXT

NAMESPACES = {"http://schemas.openxmlformats.org/wordprocessingml/2006/main", "http://purl.oclc.org/ooxml/wordprocessingml/main"}


def main_body_text(xml):
    parser = iterparse(BytesIO(xml), events=("start", "end"), forbid_dtd=True, forbid_entities=True, forbid_external=True)
    depth, elements = 0, 0
    for event, node in parser:
        if event == "start":
            depth += 1
            elements += 1
            if depth > 128 or elements > 100_000:
                raise AppError("docx", "DOCX XML exceeds structural limits.")
        else:
            depth -= 1
    root = parser.root
    namespace = next(("{" + ns + "}" for ns in NAMESPACES if root.tag == "{" + ns + "}document"), None)
    if namespace is None:
        raise AppError("docx", "Unsupported DOCX document namespace.")
    body = root.find(namespace + "body")
    if body is None:
        raise AppError("docx", "DOCX has no main document body.")

    def paragraph(node):
        return "".join((element.text or "") if element.tag == namespace + "t" else "\t" if element.tag == namespace + "tab" else "\n"
                       for element in node.iter() if element.tag in {namespace + "t", namespace + "tab", namespace + "br", namespace + "cr"})

    def blocks(parent):
        for node in parent:
            if node.tag == namespace + "p":
                yield paragraph(node)
            elif node.tag == namespace + "tbl":
                for row in node.findall(namespace + "tr"):
                    yield " | ".join("\n".join(paragraph(p) for p in cell.iter(namespace + "p")) for cell in row.findall(namespace + "tc"))
            elif node.tag in {namespace + "sdt", namespace + "sdtContent"}:
                yield from blocks(node)

    lines, count = [], 0
    for line in blocks(body):
        count += len(line) + 1
        if count > MAX_TEXT:
            raise AppError("text_limit", "DOCX text exceeds 100,000 characters.")
        lines.append(line)
    return "\n".join(lines)
