import base64
import json

import pytest
from fastapi import HTTPException
from sqlalchemy import select
from test_progress_updates import client
from test_progress_updates import session as session

from app.modules.identity.service import AuthenticatedIdentity
from app.modules.progress import router as progress_router
from app.modules.progress.service import ProgressService
from app.modules.social import router
from app.modules.social.models import PostComment, ProfileImage, SocialModerationAudit
from app.modules.social.service import SocialService, SocialValidationError
from app.modules.training.collections_service import _marker

ADMIN = AuthenticatedIdentity("bootstrap-admin", "admin", ("admin",))


def test_bootstrap_admin_moderates_both_routes_with_audit(session):
    owner = client(session, "owner")
    social = SocialService()
    profile = social.own_profile(session, "owner").profile
    social.update_own(session, "owner", None, "Biography", True)
    post = ProgressService().create(session, "owner", "Post", "shared")
    progress_router.moderate_update(
        post.id, progress_router.ModerationInput(action="hide", reason="Reason"), session, ADMIN
    )
    assert post.moderation_status == "hidden"
    router.moderate(
        router.ModerationInput(
            target_type="post", target_id=post.id, action="restore", reason="Restored"
        ),
        session,
        ADMIN,
    )
    assert post.moderation_status == "visible"
    router.moderate(
        router.ModerationInput(
            target_type="biography", target_id=profile.id, action="hide", reason="Reason"
        ),
        session,
        ADMIN,
    )
    session.expire_all()
    assert profile.biography_moderation_status == "hidden"
    audits = session.scalars(select(SocialModerationAudit)).all()
    assert len(audits) == 3
    assert all(a.actor_subject == ADMIN.subject and a.actor_account_id is None for a in audits)
    assert owner.account.keycloak_subject == "owner"


@pytest.mark.parametrize("target_type", ["post", "comment", "biography", "image"])
def test_private_content_cannot_be_moderated_by_known_id(session, target_type):
    owner = client(session, "owner")
    social = SocialService()
    profile = social.own_profile(session, "owner").profile
    social.update_own(session, "owner", None, "Private biography", False)
    post = ProgressService().create(session, "owner", "Private post", "private")
    comment = PostComment(client_id=owner.id, progress_update_id=post.id, content="Private comment")
    session.add_all(
        [
            comment,
            ProfileImage(
                client_id=owner.id, content=b"image", media_type="image/webp", width=1, height=1
            ),
        ]
    )
    session.commit()
    target_id = {
        "post": post.id,
        "comment": comment.id,
        "biography": profile.id,
        "image": owner.id,
    }[target_type]
    with pytest.raises(HTTPException) as error:
        router.moderate(
            router.ModerationInput(target_type=target_type, target_id=target_id, action="delete"),
            session,
            ADMIN,
        )
    assert error.value.status_code == 403
    assert session.scalars(select(SocialModerationAudit)).all() == []
    assert post.content == "Private post" and comment.content == "Private comment"
    assert profile.biography == "Private biography"


def test_empty_post_returns_controlled_error(session):
    client(session, "owner")
    with pytest.raises(HTTPException) as error:
        progress_router.create_update(
            progress_router.UpdateInput(content="   ", visibility="shared"),
            session,
            AuthenticatedIdentity("owner", "owner", ("client",)),
        )
    assert error.value.status_code in {409, 422}


@pytest.mark.parametrize("identifier", [None, 7, [], {}])
def test_malformed_cursor_types_are_controlled(identifier):
    stamp = "2026-09-27T00:00:00+00:00"
    social_cursor = base64.urlsafe_b64encode(
        json.dumps({"t": stamp, "i": identifier}).encode()
    ).decode()
    training_cursor = base64.urlsafe_b64encode(json.dumps([stamp, identifier]).encode()).decode()
    with pytest.raises(SocialValidationError):
        SocialService()._cursor(social_cursor)
    with pytest.raises(ValueError, match="Invalid cursor"):
        _marker(training_cursor)


def test_excessive_cursors_are_rejected():
    with pytest.raises(SocialValidationError):
        SocialService()._cursor("x" * 513)
    with pytest.raises(ValueError):
        _marker("x" * 513)
