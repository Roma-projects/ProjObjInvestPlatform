"""Извлекает читаемый текст или базовые поля из XML, HTML и PDF реестров."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from xml.etree import ElementTree

from bs4 import BeautifulSoup
from pypdf import PdfReader


def extract_file(path: Path) -> dict[str, Any]:
    """Выбирает простой разборщик по расширению файла и возвращает текстовую копию."""
    suffix = path.suffix.lower()
    if suffix == ".xml":
        root = ElementTree.parse(path).getroot()
        return {"text": " ".join(value.strip() for value in root.itertext() if value.strip()),
                "xml_fields": {element.tag.split("}")[-1]: element.text.strip()
                               for element in root.iter() if element.text and element.text.strip()}}
    if suffix == ".pdf":
        reader = PdfReader(str(path))
        return {"text": "\n".join(page.extract_text() or "" for page in reader.pages)}
    if suffix in {".html", ".htm"}:
        soup = BeautifulSoup(path.read_bytes(), "lxml")
        return {"text": soup.get_text(" ", strip=True)}
    return {"text": path.read_text(encoding="utf-8", errors="replace")}
