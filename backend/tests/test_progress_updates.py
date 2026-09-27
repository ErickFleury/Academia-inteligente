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
    service.moderate(session, shared.id, "hide", "Conteúdo inadequado")
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
    progress.moderate(session, hidden.id, "hide", "moderado")
    deleted = progress.create(session, "public", "Excluído", "shared")
    progress.own_change(session, "public", deleted.id, None, None, delete=True)

    with pytest.raises(SocialNotFoundError):
        social.instructor_post_detail(session, "instructor", private_post.id)
