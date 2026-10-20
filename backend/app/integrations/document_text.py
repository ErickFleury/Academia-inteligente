"""Resource-bounded local extraction in a disposable process; no network access needed."""

import json
import os
import subprocess
import sys


def reference_limit(name: str, ceiling: int) -> int:
    """Operators may lower pilot limits; larger capacity needs separate validation."""
    value = int(os.environ.get(name, str(ceiling)))
    if not 1 <= value <= ceiling:
        raise ValueError(f"{name} must be between 1 and {ceiling}")
    return value


MAX_UPLOAD_BYTES = reference_limit("AI_REFERENCE_MAX_UPLOAD_MIB", 20) * 1024 * 1024
MAX_TEXT_CHARACTERS = reference_limit("AI_REFERENCE_MAX_CHARACTERS", 2_000_000)
MAX_PAGES = reference_limit("AI_REFERENCE_MAX_PDF_PAGES", 500)
MEDIA_TYPES = {"application/pdf", "text/plain", "text/markdown"}


class DocumentError(Exception):
    pass


def extract_document(raw: bytes, media_type: str) -> list[dict[str, str]]:
    if media_type not in MEDIA_TYPES or not raw or len(raw) > MAX_UPLOAD_BYTES:
        raise DocumentError("document_invalid")
    try:
        result = subprocess.run(
            [sys.executable, "-m", "app.integrations.document_text", media_type],
            input=raw,
            capture_output=True,
            timeout=25,
            check=False,
        )
        if result.returncode or len(result.stdout) > 16_000_000:
            raise DocumentError("document_extraction_failed")
        pages = json.loads(result.stdout)
        if not pages or not any(p["text"].strip() for p in pages):
            raise DocumentError("document_no_text")
        return pages
    except (subprocess.TimeoutExpired, OSError, ValueError):
        raise DocumentError("document_extraction_failed") from None


def _main():
    import resource
    from io import BytesIO

    resource.setrlimit(resource.RLIMIT_AS, (768 * 1024 * 1024, 768 * 1024 * 1024))
    resource.setrlimit(resource.RLIMIT_CPU, (20, 20))
    raw = sys.stdin.buffer.read(MAX_UPLOAD_BYTES + 1)
    if len(raw) > MAX_UPLOAD_BYTES:
        raise ValueError
    if sys.argv[1] == "application/pdf":
        from pypdf import PdfReader

        reader = PdfReader(BytesIO(raw), strict=True)
        if reader.is_encrypted or len(reader.pages) > MAX_PAGES:
            raise ValueError
        pages = []
        total = 0
        for index, page in enumerate(reader.pages):
            text = page.extract_text() or ""
            total += len(text)
            if total > MAX_TEXT_CHARACTERS:
                raise ValueError
            pages.append({"location": f"page:{index + 1}", "text": text})
    else:
        text = raw.decode("utf-8-sig")
        if len(text) > MAX_TEXT_CHARACTERS or "\x00" in text:
            raise ValueError
        pages = [{"location": "text", "text": text}]
    sys.stdout.write(json.dumps(pages, ensure_ascii=True))


if __name__ == "__main__":
    try:
        _main()
    except Exception:
        # Never emit document contents or parser errors into the parent logs.
        sys.exit(1)
