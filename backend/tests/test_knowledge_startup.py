"""Exercise the startup entry point without models imported by other test modules."""

import os
import subprocess
import sys
from pathlib import Path
from textwrap import dedent

import pytest

from app.integrations.embeddings import EmbeddingProviderError
from app.modules.knowledge import startup


def test_fresh_interpreter_initializes_catalogue_after_migrations_and_on_restart():
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            dedent(
                """
                import sys

                assert "app.modules.clients.models" not in sys.modules

                from sqlalchemy import func, select
                from sqlalchemy.orm import Session

                from app.database import Base, engine
                from app.modules.knowledge import bootstrap, startup
                from app.modules.knowledge.models import KnowledgeChunk, KnowledgeSource

                events = []

                def migrate(command, *, check):
                    assert command == [sys.executable, "-m", "alembic", "upgrade", "head"]
                    assert check is True
                    events.append("migrate")
                    Base.metadata.create_all(engine)

                class FakeEmbeddings:
                    def embed(self, texts):
                        assert events[0] == "migrate"
                        events.append("embed")
                        return [[1.0] + [0.0] * 1023 for _ in texts]

                startup.subprocess.run = migrate
                bootstrap.OllamaBgeM3EmbeddingProvider = FakeEmbeddings

                startup.main()
                embedding_calls = events.count("embed")
                assert embedding_calls > 0
                startup.main()
                assert events.count("migrate") == 2
                assert events.count("embed") == embedding_calls

                with Session(engine) as session:
                    assert session.scalar(select(func.count()).select_from(KnowledgeSource)) == 24
                    assert session.scalar(select(func.count()).select_from(KnowledgeChunk)) == 66
                """
            ),
        ],
        cwd=Path(__file__).resolve().parents[1],
        env={**os.environ, "DATABASE_URL": "sqlite+pysqlite:///:memory:"},
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_bootstrap_failure_propagates_without_a_successful_start(monkeypatch):
    events = []
    monkeypatch.setattr(startup.subprocess, "run", lambda *args, **kwargs: events.append("migrate"))
    monkeypatch.setattr(startup, "seed_demo_accounts", lambda: events.append("demo"))

    def fail():
        raise EmbeddingProviderError("embedding_unavailable")

    monkeypatch.setattr(startup, "seed_knowledge", fail)
    with pytest.raises(EmbeddingProviderError):
        startup.main()
    assert events == ["migrate", "demo"]
