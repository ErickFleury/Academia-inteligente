from collections.abc import Generator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.modules.clients.models import Account, Client
from app.modules.progress.service import ProgressForbiddenError, ProgressService
from app.modules.social.service import SocialForbiddenError, SocialService


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
        "Concluí meu treino", "Registro privado"
    }
    with pytest.raises(ProgressForbiddenError):
        service.own_change(session, "grace", shared.id, "alterado", None)
    service.moderate(session, shared.id, "hide", "Conteúdo inadequado")
    assert [update.content for update, _ in service.feed(session, "grace")] == [
        "Registro privado"
    ]
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
    social.decide_follow_request(session, "ada", social.own_profile(session, "grace").profile.id, True)
    assert social.viewer_profile(session, "grace", owner.profile.id).is_following is True
    assert private_post.id in {item.id for item in social.feed_page(session, "grace", None, 20).items}
