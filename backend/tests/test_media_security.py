import struct
import zlib
from datetime import UTC, datetime
from io import BytesIO

import pytest
from fastapi import HTTPException
from PIL import Image
from test_progress_updates import client
from test_progress_updates import session as session

from app.modules.biometrics.config import BiometricError
from app.modules.biometrics.images import normalize_capture
from app.modules.identity.service import AuthenticatedIdentity
from app.modules.progress.service import ProgressService
from app.modules.social.models import CommentImage, PostComment
from app.modules.social.router import get_comment_image
from app.modules.social.service import SocialService, SocialValidationError


def image_bytes(format="PNG"):
    output = BytesIO()
    Image.new("RGB", (2, 2), "red").save(output, format)
    return output.getvalue()


def test_unapproved_decoder_is_never_opened():
    original = Image.OPEN.copy()
    Image.init()
    old = Image.OPEN["BMP"]
    called = []

    def forbidden(*args, **kwargs):
        called.append(True)
        raise AssertionError("Unsupported decoder must not run")

    raw = image_bytes("BMP")
    try:
        Image.register_open("BMP", forbidden, old[1])
        with pytest.raises(SocialValidationError):
            SocialService().normalize_image(raw)
        with pytest.raises(BiometricError):
            normalize_capture(raw)
        assert not called
    finally:
        Image.OPEN.update(original)
        Image.OPEN["BMP"] = old


def test_decompression_bomb_warnings_and_errors_are_controlled(monkeypatch):
    raw = image_bytes()
    for maximum in (3, 1):
        monkeypatch.setattr(Image, "MAX_IMAGE_PIXELS", maximum)
        with pytest.raises(SocialValidationError):
            SocialService().normalize_image(raw)
        with pytest.raises(BiometricError):
            normalize_capture(raw)


def test_large_dimensions_rejected_before_pixel_decoding():
    def chunk(kind, payload):
        return (
            struct.pack("!I", len(payload))
            + kind
            + payload
            + struct.pack("!I", zlib.crc32(kind + payload))
        )

    raw = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack("!IIBBBBB", 5000, 5000, 8, 2, 0, 0, 0))
    raw += chunk(b"IDAT", zlib.compress(b"\0\0\0\0")) + chunk(b"IEND", b"")
    with pytest.raises(SocialValidationError, match="dimensions"):
        SocialService().normalize_image(raw)


def test_valid_media_is_normalized_without_metadata():
    output = BytesIO()
    exif = Image.Exif()
    exif[315] = "private metadata"
    Image.new("RGB", (2, 2)).save(output, "JPEG", exif=exif)
    for raw in (
        SocialService().normalize_image(output.getvalue())[0],
        normalize_capture(output.getvalue()),
    ):
        with Image.open(BytesIO(raw)) as image:
            assert not image.getexif()


def test_hidden_deleted_and_private_comment_images_follow_parent_visibility(session):
    owner = client(session, "owner")
    client(session, "viewer")
    post = ProgressService().create(session, "owner", "Post", "shared")
    comment = PostComment(progress_update_id=post.id, client_id=owner.id, content="Comment")
    session.add(comment)
    session.flush()
    session.add(
        CommentImage(
            comment_id=comment.id,
            content=b"private-image",
            media_type="image/webp",
            width=1,
            height=1,
        )
    )
    session.commit()
    viewer = AuthenticatedIdentity("viewer", None, ("client",))
    author = AuthenticatedIdentity("owner", None, ("client",))
    assert get_comment_image(comment.id, session, viewer).body == b"private-image"
    comment.moderation_status = "hidden"
    session.commit()
    with pytest.raises(HTTPException) as hidden:
        get_comment_image(comment.id, session, viewer)
    assert hidden.value.status_code == 404
    assert get_comment_image(comment.id, session, author).body == b"private-image"
    comment.moderation_status = "visible"
    SocialService().update_own(session, "owner", None, None, False)
    with pytest.raises(HTTPException) as private:
        get_comment_image(comment.id, session, viewer)
    assert private.value.status_code == 403
    comment.deleted_at = datetime.now(UTC)
    session.commit()
    with pytest.raises(HTTPException):
        get_comment_image(comment.id, session, author)
