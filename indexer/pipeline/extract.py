"""Extract page text and preserve explicit structure."""
from __future__ import annotations

import re
from pathlib import Path

from .models import Document, Page


def extract(path: str, doc_version: str, superseded: bool) -> Document:
    file = Path(path)
    doc = Document(file.name, doc_version, superseded)
    if file.suffix.lower() == ".pdf":
        import pdfplumber

        with pdfplumber.open(file) as pdf:
            for number, page in enumerate(pdf.pages, 1):
                text = page.extract_text() or ""
                ocr = not text.strip()
                if ocr and page.images:
                    import pytesseract

                    resolution = min(190.0, 72.0 * 2400 / max(page.width, page.height))
                    image = page.to_image(resolution=resolution).original
                    try:
                        text = pytesseract.image_to_string(image, config="--psm 6", timeout=25)
                    except RuntimeError:
                        text = ""
                    finally:
                        image.close()
                if not ocr:
                    tables = []
                    for table in page.find_tables():
                        rows = [" | ".join(" ".join((cell or "").split()) for cell in row)
                                for row in table.extract()]
                        if rows:
                            tables.append("\n".join(rows))
                    if tables:
                        text += "\n\n" + "\n\n".join(tables)
                doc.pages.append(Page(file.name, number, text, ocr and bool(page.images)))
                page.close()
        return doc
    text = file.read_text(encoding="utf-8-sig")
    if file.suffix.lower() == ".html":
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(text, "html.parser")
        for node in soup.select("script, style, nav, header, footer"):
            node.decompose()
        main = soup.select_one("main, #main, #content") or soup
        for heading in main.select("h1,h2,h3,h4,h5,h6"):
            heading.replace_with("\n\n## " + heading.get_text(" ", strip=True) + "\n\n")
        for row in main.select("tr"):
            row.replace_with("\n" + " | ".join(
                cell.get_text(" ", strip=True) for cell in row.select("th,td")
            ) + "\n")
        text = main.get_text("\n", strip=True)
    elif file.suffix.lower() == ".md":
        text = re.sub(r"\A---\r?\n.*?\r?\n---(?:\r?\n|$)", "", text, count=1, flags=re.S)
    doc.pages.append(Page(file.name, 1, text))
    return doc
