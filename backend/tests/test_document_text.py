from io import BytesIO

import pytest
from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

from app.integrations.document_text import DocumentError, extract_document


def text_pdf(page_count):
    writer = PdfWriter()
    page = writer.add_blank_page(width=300, height=300)
    font = DictionaryObject(
        {
            NameObject("/Type"): NameObject("/Font"),
            NameObject("/Subtype"): NameObject("/Type1"),
            NameObject("/BaseFont"): NameObject("/Helvetica"),
        }
    )
    page[NameObject("/Resources")] = DictionaryObject(
        {NameObject("/Font"): DictionaryObject({NameObject("/F1"): font})}
    )
    content = DecodedStreamObject()
    content.set_data(b"BT /F1 12 Tf 10 100 Td (Reference text.) Tj ET")
    page[NameObject("/Contents")] = content
    for _ in range(page_count - 1):
        writer.add_blank_page(width=300, height=300)
    raw = BytesIO()
    writer.write(raw)
    return raw.getvalue()


def test_extracts_one_thousand_pages_preserving_page_locations(monkeypatch):
    monkeypatch.delenv("AI_REFERENCE_MAX_PDF_PAGES", raising=False)
    pages = extract_document(text_pdf(1000), "application/pdf")
    assert len(pages) == 1000
    assert pages[0] == {"location": "page:1", "text": "Reference text."}
    assert pages[-1]["location"] == "page:1000"


@pytest.mark.parametrize("limit,page_count", [(1000, 1001), (10, 11)])
def test_page_limit_returns_specific_error(monkeypatch, limit, page_count):
    monkeypatch.setenv("AI_REFERENCE_MAX_PDF_PAGES", str(limit))
    with pytest.raises(DocumentError, match="^document_page_limit$"):
        extract_document(text_pdf(page_count), "application/pdf")
