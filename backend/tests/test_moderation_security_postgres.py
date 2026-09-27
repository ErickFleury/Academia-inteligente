import importlib.util
import os
from pathlib import Path
from uuid import uuid4

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import text
from test_training_review_postgres import sessions as sessions

pytestmark = pytest.mark.skipif(os.getenv("TEST_POSTGRES") != "1", reason="PostgreSQL opt-in")


def test_moderation_actor_migration_preserves_old_rows_and_rejects_lossy_downgrade(sessions):
    spec = importlib.util.spec_from_file_location(
        "moderation_migration", Path("alembic/versions/20260927_29_social_moderation_actor.py")
    )
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    with sessions() as session:
        migration.op = Operations(MigrationContext.configure(session.connection()))
        migration.downgrade()
        account_id, audit_id, target_id = uuid4(), uuid4(), uuid4()
        session.execute(
            text(
                "INSERT INTO account (id, email, account_active) "
                "VALUES (:id, 'admin@example.test', true)"
            ),
            {"id": account_id},
        )
        session.execute(
            text(
                "INSERT INTO social_moderation_audit "
                "(id, actor_account_id, target_id, target_type, action) "
                "VALUES (:id, :actor, :target, 'post', 'hide')"
            ),
            {"id": audit_id, "actor": account_id, "target": target_id},
        )
        migration.upgrade()
        assert (
            session.scalar(
                text("SELECT actor_account_id FROM social_moderation_audit WHERE id = :id"),
                {"id": audit_id},
            )
            == account_id
        )
        session.execute(
            text(
                "INSERT INTO social_moderation_audit "
                "(id, actor_subject, target_id, target_type, action) "
                "VALUES (:id, 'bootstrap', :target, 'post', 'hide')"
            ),
            {"id": uuid4(), "target": target_id},
        )
        with pytest.raises(RuntimeError, match="OIDC-only"):
            migration.downgrade()
        assert session.scalar(text("SELECT count(*) FROM social_moderation_audit")) == 2


def test_full_erasure_removes_authored_audits_and_profile_target_audits(sessions):
    from sqlalchemy import select
    from test_client_erasure import DeletingProvisioner
    from test_progress_updates import client

    from app.modules.clients.models import Account
    from app.modules.clients.service import ClientService
    from app.modules.progress.service import ProgressService
    from app.modules.social.models import SocialModerationAudit
    from app.modules.social.service import SocialService

    with sessions() as session:
        owner = client(session, "owner")
        client(session, "other")
        profile = SocialService().own_profile(session, "owner").profile
        other_post = ProgressService().create(session, "other", "Keep this post", "shared")
        SocialService().moderate(session, "bootstrap", "biography", profile.id, "hide", "Reason")
        SocialService().moderate(session, "owner", "post", other_post.id, "hide", "Reason")
        owner_id, account_id = owner.id, owner.account_id
        assert ClientService(DeletingProvisioner()).erase(session, owner_id)
        assert session.get(Account, account_id) is None
        assert session.scalars(select(SocialModerationAudit)).all() == []
        assert other_post.content == "Keep this post"
