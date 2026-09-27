"""Shared bounded decoder for ordinary catalog/social images, never biometrics."""

import warnings
from io import BytesIO

from PIL import Image, ImageOps, UnidentifiedImageError


class ImageValidationError(Exception):
    pass


def normalize_image(raw: bytes) -> tuple[bytes, str, int, int]:
    if not raw or len(raw) > 5 * 1024 * 1024:
        raise ImageValidationError("Image size is invalid")
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(BytesIO(raw), formats=("JPEG", "PNG", "WEBP")) as source:
                if getattr(source, "n_frames", 1) != 1:
                    raise ImageValidationError("Unsupported image")
                if source.width * source.height > 4096 * 4096:
                    raise ImageValidationError("Image dimensions are too large")
                source.verify()
            with Image.open(BytesIO(raw), formats=("JPEG", "PNG", "WEBP")) as source:
                image = ImageOps.exif_transpose(source).convert("RGB")
                image.thumbnail((1024, 1024))
                clean = Image.new("RGB", image.size)
                clean.paste(image)
                output = BytesIO()
                clean.save(output, format="WEBP", quality=88, method=6)
                return output.getvalue(), "image/webp", clean.width, clean.height
    except (
        UnidentifiedImageError,
        OSError,
        ValueError,
        Image.DecompressionBombError,
        Image.DecompressionBombWarning,
    ):
        raise ImageValidationError("Invalid image") from None
