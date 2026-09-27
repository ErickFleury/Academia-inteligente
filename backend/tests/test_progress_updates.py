from collections.abc import Generator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.modules.clients.models import Account, Client, Employee
from app.modules.progress.service import ProgressForbiddenError, ProgressService
from app.modules.social.models import PostImage
from app.modules.social.service import (
    SocialForbiddenError,
    SocialNotFoundError,
    SocialService,
    SocialValidationError,
)


@pytest.fixture
def session() -> Generator[Session, None, None]:
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    value = sessionmaker(bind=engine, expire_on_commit=False)()
    yield value
    value.close()
    Base.metadata.drop_all(engine)
    engine.dispose()


def client(session: Session, subject: str) -> Client:
    value = Client(
        name=subject,
        account=Account(
            email=f"{subject}@example.test", keycloak_subject=subject, account_active=True
        ),
    )
    session.add(value)
    session.commit()
    return value


def test_private_shared_and_author_moderation_policies(session: Session) -> None:
    client(session, "ada")
    client(session, "grace")
    service = ProgressService()
    social = SocialService()
    social.update_own(session, "ada", None, None, False)
    private = service.create(session, "ada", "Registro privado", "private")
    assert service.feed(session, "grace") == []
    social.update_own(session, "ada", None, None, True)
    shared = service.create(session, "ada", "Concluí meu treino", "shared")
    assert {update.content for update, _ in service.feed(session, "grace")} == {
        "Concluí meu treino",
        "Registro privado",
    }
    with pytest.raises(ProgressForbiddenError):
        service.own_change(session, "grace", shared.id, "alterado", None)
    service.moderate(session, shared.id, "hide", "Conteúdo inadequado", actor_subject="admin")
    assert [update.content for update, _ in service.feed(session, "grace")] == ["Registro privado"]
    own_feed = service.feed(session, "ada")
    assert {update.id for update, _ in own_feed} == {private.id, shared.id}
    service.own_change(session, "ada", private.id, None, None, delete=True)
    assert private.id not in {update.id for update, _ in service.feed(session, "ada")}


def test_private_account_requires_accepted_follow_request(session: Session) -> None:
    client(session, "ada")
    client(session, "grace")
    social = SocialService()
    progress = ProgressService()
    owner = social.own_profile(session, "ada")
    social.update_own(session, "ada", None, None, False)
    private_post = progress.create(session, "ada", "Somente seguidores", "shared")
    with pytest.raises(SocialForbiddenError):
        social.viewer_profile(session, "grace", owner.profile.id)
    pending = social.follow(session, "grace", owner.profile.id, True)
    assert pending.follow_requested is True
    assert [item.client.name for item in social.follow_requests(session, "ada")] == ["grace"]
    social.decide_follow_request(
        session, "ada", social.own_profile(session, "grace").profile.id, True
    )
    assert social.viewer_profile(session, "grace", owner.profile.id).is_following is True
    assert private_post.id in {
        item.id for item in social.feed_page(session, "grace", None, 20).items
    }


def test_only_author_can_remove_post_image_and_post_keeps_content_or_media(
    session: Session,
) -> None:
    client(session, "ada")
    client(session, "grace")
    progress = ProgressService()
    social = SocialService()
    update = progress.create(session, "ada", "Com imagem", "private")
    image = PostImage(
        progress_update_id=update.id,
        position=0,
        content=b"placeholder",
        media_type="image/webp",
        width=1,
        height=1,
    )
    session.add(image)
    session.commit()

    with pytest.raises(SocialForbiddenError):
        social.remove_post_image(session, "grace", update.id, image.id)

    removed = social.remove_post_image(session, "ada", update.id, image.id)
    assert social.post_images(session, update.id) == []
    assert removed.edited_at is not None

    image_only = progress.create(session, "ada", "Mantém o texto", "private")
    image = PostImage(
        progress_update_id=image_only.id,
        position=0,
        content=b"placeholder",
        media_type="image/webp",
        width=1,
        height=1,
    )
    session.add(image)
    session.commit()
    image_only.content = None
    session.commit()

    with pytest.raises(SocialValidationError):
        social.remove_post_image(session, "ada", image_only.id, image.id)


def test_instructor_feed_excludes_private_profiles_hidden_and_deleted_posts(
    session: Session,
) -> None:
    public = client(session, "public")
    client(session, "private")
    instructor_account = Account(
        email="instructor@example.test", keycloak_subject="instructor", account_active=True
    )
    instructor_account.employee = Employee(specialization="instructor", active=True)
    session.add(instructor_account)
    session.commit()
    progress = ProgressService()
    social = SocialService()
    social.own_profile(session, "public")
    social.update_own(session, "public", None, None, True)
    assert social.profile_for_client(session, public.id).visible_to_clients is True
    assert public.active is True
    public_post = progress.create(session, "public", "Visível", "shared")
    assert public_post.visibility == "shared"
    assert public_post.moderation_status == "visible"
    private_post = progress.create(session, "private", "Privado", "shared")
    social.update_own(session, "private", None, None, False)
    page = social.instructor_feed_page(session, "instructor", None, 20)
    assert [item.id for item in page.items] == [public_post.id]
    assert private_post.id not in {item.id for item in page.items}
    hidden = progress.create(session, "public", "Oculto", "shared")
    progress.moderate(session, hidden.id, "hide", "moderado", actor_subject="admin")
    deleted = progress.create(session, "public", "Excluído", "shared")
    progress.own_change(session, "public", deleted.id, None, None, delete=True)

    with pytest.raises(SocialNotFoundError):
        social.instructor_post_detail(session, "instructor", private_post.id)


def test_instructor_pagination_filters_private_posts_before_limit(session):
    from datetime import UTC, datetime, timedelta

    from sqlalchemy import select
    from training_fixtures import instructor

    from app.modules.progress.models import ProgressUpdate

    instructor(session, "instructor")
    client(session, "public")
    client(session, "private")
    progress, social = ProgressService(), SocialService()
    social.update_own(session, "public", None, None, True)
    social.update_own(session, "private", None, None, False)
    public_posts = [
        progress.create(session, "public", f"Público {index}", "shared").id for index in range(3)
    ]
    for index in range(6):
        progress.create(session, "private", f"Privado {index}", "shared")
    # Explicit timestamps use the same bind representation in SQLite; PostgreSQL
    # stores native timestamptz. Do not depend on SQLite CURRENT_TIMESTAMP text.
    for index, post in enumerate(session.scalars(select(ProgressUpdate))):
        post.created_at = datetime(2026, 9, 27, 12, tzinfo=UTC) + timedelta(seconds=index)
    session.commit()
    first = social.instructor_feed_page(session, "instructor", None, 2)
    assert len(first.items) == 2 and not first.end_reached and first.next_cursor
    second = social.instructor_feed_page(session, "instructor", first.next_cursor, 2)
    assert len(second.items) == 1 and second.end_reached
    assert {item.id for item in first.items + second.items} == set(public_posts)


def test_instructor_comment_media_checks_parent_privacy_and_moderation(session):
    from fastapi import HTTPException
    from training_fixtures import instructor

    from app.modules.employees import instructor_social_router as router
    from app.modules.identity.service import AuthenticatedIdentity
    from app.modules.social.models import CommentImage, PostComment

    instructor(session, "instructor")
    owner = client(session, "public")
    progress, social = ProgressService(), SocialService()
    social.update_own(session, "public", None, None, True)
    post = progress.create(session, "public", "Público", "shared")
    other = progress.create(session, "public", "Outro", "shared")
    comment = PostComment(progress_update_id=post.id, client_id=owner.id, content="Comentário")
    session.add(comment)
    session.flush()
    session.add(
        CommentImage(
            comment_id=comment.id,
            content=b"synthetic-image",
            media_type="image/webp",
            width=1,
            height=1,
        )
    )
    session.commit()
    identity = AuthenticatedIdentity("instructor", "test", ("instructor",))
    assert router.detail(post.id, session, identity).comments[0].image.id == comment.id
    assert router.comment_image(post.id, comment.id, session, identity).body == b"synthetic-image"
    with pytest.raises(HTTPException) as wrong:
        router.comment_image(other.id, comment.id, session, identity)
    assert wrong.value.status_code == 404
    comment.moderation_status = "hidden"
    session.commit()
    with pytest.raises(HTTPException):
        router.comment_image(post.id, comment.id, session, identity)
    comment.moderation_status = "visible"
    session.commit()
    social.update_own(session, "public", None, None, False)
    with pytest.raises(HTTPException):
        router.comment_image(post.id, comment.id, session, identity)
