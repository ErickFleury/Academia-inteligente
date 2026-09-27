"""Bounded in-memory webcam transport; no filesystem or biometric logging."""

import warnings
from email import policy
from email.parser import BytesParser
from io import BytesIO
from uuid import UUID

from fastapi import Request
from PIL import Image, ImageOps, UnidentifiedImageError

from app.modules.biometrics.config import BiometricError

MAX_CAPTURE_BYTES = 5 * 1024 * 1024


def normalize_capture(raw: bytes) -> bytes:
    if not raw or len(raw) > MAX_CAPTURE_BYTES:
        raise BiometricError("capture_size_invalid", 422)
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(BytesIO(raw), formats=("JPEG", "PNG")) as source:
                if (
                    source.format not in {"JPEG", "PNG"}
                    or getattr(source, "n_frames", 1) != 1
                    or not 1 <= source.width <= 4096
                    or not 1 <= source.height <= 4096
                ):
                    raise ValueError
                source.load()
                # New pixels discard EXIF, comments, profiles, and ancillary metadata.
                pixels = ImageOps.exif_transpose(source).convert("RGB")
                clean = Image.new("RGB", pixels.size)
                clean.paste(pixels)
                output = BytesIO()
                clean.save(output, "JPEG", quality=90)
                result = output.getvalue()
                if len(result) > MAX_CAPTURE_BYTES:
                    raise ValueError
                return result
    except (
        OSError,
        ValueError,
        UnidentifiedImageError,
        Image.DecompressionBombError,
        Image.DecompressionBombWarning,
    ):
        raise BiometricError("capture_invalid", 422) from None


async def read_capture(request: Request) -> tuple[UUID, bytes]:
    """Accept exactly two bounded multipart parts without a new parser dependency."""
    content_type = request.headers.get("content-type", "")
    if len(content_type) > 200 or "\r" in content_type or "\n" in content_type:
        raise BiometricError("capture_invalid", 422)
    data = bytearray()
    async for chunk in request.stream():
        if len(data) + len(chunk) > MAX_CAPTURE_BYTES + 8192:
            raise BiometricError("capture_size_invalid", 422)
        data.extend(chunk)
    try:
        message = BytesParser(policy=policy.default).parsebytes(
            b"Content-Type: "
            + content_type.encode("ascii")
            + b"\r\nMIME-Version: 1.0\r\n\r\n"
            + bytes(data)
        )
        if message.get_content_type() != "multipart/form-data" or message.defects:
            raise ValueError
        parts = list(message.iter_parts())
        if len(parts) != 2:
            raise ValueError
        fields = {}
        for part in parts:
            name = part.get_param("name", header="content-disposition")
            if (
                part.is_multipart()
                or part.defects
                or name not in {"file", "command_id"}
                or name in fields
                or part.get_content_disposition() != "form-data"
                or part.get("Content-Transfer-Encoding") is not None
            ):
                raise ValueError
            fields[name] = part.get_payload(decode=True)
        if len(fields["command_id"]) > 36:
            raise ValueError
        return UUID(fields["command_id"].decode("ascii")), normalize_capture(fields["file"])
    except (ValueError, KeyError, TypeError, UnicodeError):
        raise BiometricError("capture_invalid", 422) from None
