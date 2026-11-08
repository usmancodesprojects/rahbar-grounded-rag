"""Extract page text and preserve explicit structure."""
from __future__ import annotations

import re
from pathlib import Path

from .models import Document, Page


def extract(path: str, doc_version: str, superseded: bool) -> Document:
    file = Path(path)
    doc = Document(file.name, doc_version, superseded)
    if file.suffix.lower() == ".pdf":
        import pypdfium2

        with pypdfium2.PdfDocument(file) as pdf:
            for index in range(len(pdf)):
                page = pdf[index]
                textpage = page.get_textpage()
                text = textpage.get_text_bounded()
                textpage.close()
                ocr = not text.strip() and any(page.get_objects(
                    filter=[pypdfium2.raw.FPDF_PAGEOBJ_IMAGE], max_depth=4
                ))
                if ocr:
                    import pytesseract

                    scale = min(190 / 72, 2400 / max(page.get_size()))
                    bitmap = page.render(scale=scale)
                    image = bitmap.to_pil()
                    try:
                        text = pytesseract.image_to_string(image, config="--psm 6", timeout=25)
                    except RuntimeError:
                        text = ""
                    finally:
                        image.close()
                        bitmap.close()
                doc.pages.append(Page(file.name, index + 1, text, ocr))
                page.close()
        return doc
    text = file.read_text(encoding="utf-8-sig")
    if file.suffix.lower() == ".html":
        from bs4 import BeautifulSoup, NavigableString

        soup = BeautifulSoup(text, "html.parser")
        for node in soup.select("script, style, nav, header, footer"):
            node.decompose()
        main = soup.select_one("main, #main, #content") or soup
        for heading in main.select("h1,h2,h3,h4,h5,h6"):
            heading.replace_with(NavigableString("\n\n## " + heading.get_text(" ", strip=True) + "\n\n"))
        for row in main.select("tr"):
            row.replace_with(NavigableString("\n" + " | ".join(
                cell.get_text(" ", strip=True) for cell in row.select("th,td")
            ) + "\n"))
        text = main.get_text("\n", strip=True)
    elif file.suffix.lower() == ".md":
        text = re.sub(r"\A---\r?\n.*?\r?\n---(?:\r?\n|$)", "", text, count=1, flags=re.S)
    doc.pages.append(Page(file.name, 1, text))
    return doc
