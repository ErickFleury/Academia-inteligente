"""Reference lifecycle, bounded imports, and active-version-only retrieval."""

from __future__ import annotations

import math
import re
import unicodedata
from collections import Counter
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import Float, Text, case, delete, func, literal_column, select, text
from sqlalchemy.dialects.postgresql import TSQUERY
from sqlalchemy.orm import Session

from app.integrations.ai import AiProviderError
from app.integrations.document_text import (
    MAX_UPLOAD_BYTES,
    MEDIA_TYPES,
    DocumentError,
    extract_document,
    reference_limit,
)
from app.integrations.embeddings import EmbeddingProvider, HttpEmbeddingProvider
from app.modules.knowledge.models import ReferencePassage, ReferenceSource, ReferenceVersion


class KnowledgeError(Exception):
    def __init__(self, code: str, status: int = 400):
        super().__init__(code)
        self.code, self.status = code, status


def searchable_text(value):
    # Match accented client questions and unaccented router keywords without
    # introducing another PostgreSQL extension. Keep the GIN migration in sync.
    return func.translate(
        func.lower(value),
        literal_column("'áàâãäéèêëíìîïóòôõöúùûüçñ'"),
        literal_column("'aaaaaeeeeiiiiooooouuuucn'"),
    )


def catalog_lock(session: Session):
    if session.bind.dialect.name == "postgresql":
        session.execute(text("SELECT pg_advisory_xact_lock(1421407001)"))


def section_blocks(pages):
    """Carry explicit chapter/Markdown headings, never infer client applicability."""
    repeated = Counter(line.strip() for page in pages for line in set(page["text"].splitlines()))
    section = ""
    markdown_headings = {}
    for page in pages:
        lines = page["text"].splitlines()
        # PDF chapters often put the chapter marker below the heading. Ignore
        # tables of contents and repeating running headers.
        chapter = any(
            re.fullmatch(r"\s*(?:\d+\s*)?CAP[IÍ]TULO(?:\s+\d+)?\s*", line) for line in lines
        )
        if chapter and not any("___" in line for line in lines):
            candidates = [
                line.strip()
                for line in lines
                if line.strip().isupper()
                and 12 <= len(line.strip()) <= 140
                and repeated[line.strip()] == 1
                and not line.strip().endswith(("?", ":"))
                and len(line.split()) >= 3
            ]
            # Include a wrapped heading such as "E MULHERES NO PÓS-PARTO".
            section = " ".join(candidates[:2])[:280] if candidates else ""
        block = []
        for line in lines:
            heading = re.match(r"^(#{1,6})\s+(.+?)\s*#*\s*$", line)
            if heading:
                if block:
                    yield page["location"], section, "\n".join(block)
                level = len(heading[1])
                markdown_headings = {k: v for k, v in markdown_headings.items() if k < level}
                markdown_headings[level] = heading[2]
                section = " / ".join(markdown_headings.values())[:280]
                block = []
            block.append(line)
        if block:
            yield page["location"], section, "\n".join(block)


def passages(pages: list[dict[str, str]]):
    """Keep section provenance within each bounded passage, including continuation pages."""
    position = 0
    for location, section, block in section_blocks(pages):
        prefix = f"Seção: {section}\n" if section else ""
        remaining = block.strip()
        while remaining:
            # At most 1000 Unicode characters / 4000 UTF-8 bytes plus prefix.
            end = min(len(remaining), 1000 - len(prefix))
            if end < len(remaining):
                boundary = max(remaining.rfind("\n", 400, end), remaining.rfind(". ", 400, end))
                if boundary > 0:
                    end = boundary + 1
            content, remaining = remaining[:end].strip(), remaining[end:].lstrip()
            if content:
                position += 1
                yield position, f"{location};passage:{position}", prefix + content


def section_terms(value):
    normalized = unicodedata.normalize("NFKD", value.casefold())
    words = set(
        re.findall(r"[a-z0-9]+", "".join(c for c in normalized if not unicodedata.combining(c)))
    )
    return words - {
        "a",
        "as",
        "o",
        "os",
        "de",
        "da",
        "das",
        "do",
        "dos",
        "e",
        "em",
        "para",
        "por",
        "com",
        "que",
        "qual",
        "quais",
        "como",
        "segundo",
        "guia",
        "atividade",
        "atividades",
        "fisica",
        "fisicas",
    }


def section_match(content, query):
    if not content.startswith("Seção: "):
        return 0
    heading = content.split("\n", 1)[0][7:]
    return len(section_terms(heading) & section_terms(query))


class KnowledgeService:
    def __init__(self, provider: EmbeddingProvider | None = None):
        self.provider = provider or HttpEmbeddingProvider()

    def upload(self, session, *, title, media_type, raw, source_id=None):
        if not title.strip() or len(title) > 200 or media_type not in MEDIA_TYPES:
            raise KnowledgeError("document_invalid")
        if not raw or len(raw) > MAX_UPLOAD_BYTES:
            raise KnowledgeError("document_size", 413)
        catalog_lock(session)
        queued = session.scalar(
            select(func.count())
            .select_from(ReferenceVersion)
            .where(ReferenceVersion.status.in_(["pending", "processing"]))
        )
        if queued >= 20:
            raise KnowledgeError("import_queue_full", 429)
        if source_id is None:
            source = ReferenceSource(title=title.strip())
            session.add(source)
            session.flush()
        else:
            source = session.get(ReferenceSource, source_id)
            if source is None:
                raise KnowledgeError("reference_not_found", 404)
        number = (
            session.scalar(
                select(func.max(ReferenceVersion.number)).where(
                    ReferenceVersion.source_id == source.id
                )
            )
            or 0
        ) + 1
        version = ReferenceVersion(
            source_id=source.id, number=number, raw_content=raw, media_type=media_type
        )
        session.add(version)
        session.commit()
        return self.describe(session, version)

    def describe(self, session, version):
        source = session.get(ReferenceSource, version.source_id)
        return {
            "id": version.id,
            "source_id": source.id,
            "title": source.title,
            "number": version.number,
            "status": version.status,
            "active": version.active,
            "progress": version.progress,
            "error_code": version.error_code,
            "revision": source.revision,
            "embedding_fingerprint": version.embedding_fingerprint,
        }

    def list(self, session):
        versions = session.scalars(
            select(ReferenceVersion).order_by(ReferenceVersion.updated_at.desc()).limit(500)
        ).all()
        return [self.describe(session, version) for version in versions]

    def preview(self, session, version_id, offset=0):
        if session.get(ReferenceVersion, version_id) is None:
            raise KnowledgeError("reference_not_found", 404)
        rows = session.scalars(
            select(ReferencePassage)
            .where(ReferencePassage.version_id == version_id)
            .order_by(ReferencePassage.position)
            .offset(offset)
            .limit(20)
        ).all()
        return [
            {"position": p.position, "location": p.location, "content": p.content} for p in rows
        ]

    def transition(self, session, version_id, action, revision):
        catalog_lock(session)
        version = session.scalar(
            select(ReferenceVersion).where(ReferenceVersion.id == version_id).with_for_update()
        )
        if version is None:
            raise KnowledgeError("reference_not_found", 404)
        source = session.scalar(
            select(ReferenceSource).where(ReferenceSource.id == version.source_id).with_for_update()
        )
        if source.revision != revision:
            raise KnowledgeError("reference_conflict", 409)
        if action == "activate":
            if (
                version.status != "ready"
                or version.embedding_fingerprint != self.provider.config.fingerprint
            ):
                raise KnowledgeError("reference_not_ready", 409)
            active = session.scalars(
                select(ReferenceVersion).where(
                    ReferenceVersion.source_id == source.id, ReferenceVersion.active.is_(True)
                )
            ).all()
            if not active:
                total = session.scalar(
                    select(func.count())
                    .select_from(ReferenceVersion)
                    .where(ReferenceVersion.active.is_(True))
                )
                if total >= reference_limit("AI_REFERENCE_MAX_ACTIVE_DOCUMENTS", 100):
                    raise KnowledgeError("reference_capacity", 409)
            for old in active:
                old.active, old.status = False, "withdrawn"
            session.flush()
            version.active, version.status = True, "active"
        elif action == "withdraw":
            version.active, version.status = False, "withdrawn"
            version.generation += 1  # Cancel any in-flight worker publication.
        elif action == "retry":
            if version.active or version.status == "processing":
                raise KnowledgeError("reference_conflict", 409)
            version.generation += 1
            version.status, version.error_code, version.progress = "pending", None, 0
        else:
            raise KnowledgeError("reference_action_invalid")
        source.revision += 1
        session.commit()
        return self.describe(session, version)

    def import_next(self, sessions) -> bool:
        """Claim one persisted job. Another process can recover an expired lease."""
        with sessions() as session:
            stale = datetime.now(UTC) - timedelta(minutes=20)
            candidate = session.scalar(
                select(ReferenceVersion)
                .where(
                    (ReferenceVersion.status == "pending")
                    | (
                        (ReferenceVersion.status == "processing")
                        & (ReferenceVersion.updated_at < stale)
                    )
                )
                .order_by(ReferenceVersion.updated_at)
                .with_for_update(skip_locked=True)
                .limit(1)
            )
            if candidate is None:
                return False
            candidate.generation += 1
            candidate.status, candidate.started_at = "processing", datetime.now(UTC)
            candidate.error_code, candidate.progress = None, 0
            version_id, generation = candidate.id, candidate.generation
            raw, media_type = candidate.raw_content, candidate.media_type
            session.execute(
                delete(ReferencePassage).where(ReferencePassage.version_id == version_id)
            )
            session.commit()
        try:
            chunks = list(passages(extract_document(raw, media_type)))
            if not chunks:
                raise DocumentError("document_no_text")
            for start in range(0, len(chunks), 16):
                batch = chunks[start : start + 16]
                vectors = self.provider.embed([p[2] for p in batch], purpose="document")
                with sessions() as session:
                    current = session.scalar(
                        select(ReferenceVersion)
                        .where(ReferenceVersion.id == version_id)
                        .with_for_update()
                    )
                    if current is None or current.generation != generation:
                        return True
                    for (position, location, content), vector in zip(batch, vectors, strict=True):
                        session.add(
                            ReferencePassage(
                                version_id=version_id,
                                position=position,
                                location=location,
                                content=content,
                                embedding=vector,
                            )
                        )
                    current.progress = min(99, math.floor((start + len(batch)) * 100 / len(chunks)))
                    session.commit()
            with sessions() as session:
                current = session.scalar(
                    select(ReferenceVersion)
                    .where(ReferenceVersion.id == version_id)
                    .with_for_update()
                )
                if current is not None and current.generation == generation:
                    current.status, current.progress = "ready", 100
                    current.embedding_fingerprint = self.provider.config.fingerprint
                    current.embedding_dimensions = self.provider.config.dimensions
                    session.commit()
        except (AiProviderError, DocumentError) as error:
            with sessions() as session:
                current = session.scalar(
                    select(ReferenceVersion)
                    .where(ReferenceVersion.id == version_id)
                    .with_for_update()
                )
                if current is not None and current.generation == generation:
                    current.status = "failed"
                    current.error_code = (
                        error.category if isinstance(error, AiProviderError) else str(error)
                    )
                    session.execute(
                        delete(ReferencePassage).where(ReferencePassage.version_id == version_id)
                    )
                    session.commit()
        return True

    def search(self, session: Session, query: str, *, timeout: float = 10, limit: int = 5):
        if not query.strip() or len(query) > 500 or not 1 <= limit <= 10:
            raise KnowledgeError("reference_query_invalid")
        base = (
            select(ReferencePassage)
            .join(ReferenceVersion)
            .where(ReferenceVersion.active.is_(True), ReferenceVersion.status == "active")
        )
        if session.bind.dialect.name == "postgresql":
            document = func.to_tsvector(
                text("'portuguese'::regconfig"), searchable_text(ReferencePassage.content)
            )
            # Natural questions contain words absent from an otherwise relevant
            # passage. Match Portuguese lexemes disjunctively and rank overlap;
            # requiring every word discarded exact equipment/error-code matches.
            plain = func.plainto_tsquery(text("'portuguese'::regconfig"), searchable_text(query))
            # Cast the already-normalized lexemes instead of stemming them a
            # second time (which turns "série" -> "seri" -> a different lexeme).
            terms = func.replace(plain.cast(Text), " & ", " | ").cast(TSQUERY)
            lexical = session.scalars(
                base.where(document.op("@@")(terms))
                .order_by(func.ts_rank_cd(document, terms).desc(), ReferencePassage.id)
                .limit(20)
            ).all()
        else:
            # SQLite is only the deterministic unit-test dialect; production uses PostgreSQL.
            terms = set(re.findall(r"\w+", query.casefold()))
            rows = session.scalars(base).all()
            lexical = sorted(
                (r for r in rows if terms & set(re.findall(r"\w+", r.content.casefold()))),
                key=lambda r: -len(terms & set(re.findall(r"\w+", r.content.casefold()))),
            )[:20]
        semantic = []
        try:
            query_vector = self.provider.embed([query], purpose="query", timeout=timeout)[0]
            compatible = base.where(
                ReferenceVersion.embedding_fingerprint == self.provider.config.fingerprint
            )
            if session.bind.dialect.name == "postgresql":
                # CASE prevents the database from evaluating vector distance on
                # old dimensions before applying the namespace WHERE predicate.
                distance = case(
                    (
                        ReferenceVersion.embedding_fingerprint == self.provider.config.fingerprint,
                        ReferencePassage.embedding.op("OPERATOR(public.<=>)", return_type=Float)(
                            query_vector
                        ),
                    ),
                    else_=None,
                )
                semantic = session.scalars(
                    compatible.where(distance <= 0.45)
                    .order_by(distance, ReferencePassage.id)
                    .limit(20)
                ).all()
            else:

                def distance(row):
                    a, b = row.embedding, query_vector
                    return 1 - sum(x * y for x, y in zip(a, b, strict=True)) / (
                        math.sqrt(sum(x * x for x in a)) * math.sqrt(sum(y * y for y in b))
                    )

                semantic = sorted(
                    (r for r in session.scalars(compatible) if distance(r) <= 0.45), key=distance
                )[:20]
        except AiProviderError:
            pass  # Explicit lexical-only degradation; never switch provider.
        scores, candidates = {}, {}
        for ranking in (lexical, semantic):
            for rank, passage in enumerate(ranking, 1):
                candidates[passage.id] = passage
                scores[passage.id] = scores.get(passage.id, 0) + 1 / (60 + rank)
        # Heading matches boost applicability without filtering out conflicting
        # evidence from other sources or relying on inferred personal attributes.
        ranked = sorted(
            scores,
            key=lambda key: (
                -(scores[key] * (1 + 0.5 * min(3, section_match(candidates[key].content, query)))),
                str(key),
            ),
        )
        selected, seen = [], set()
        for key in ranked:
            passage = candidates[key]
            identity = (passage.version_id, " ".join(passage.content.split()))
            if identity not in seen:
                selected.append(key)
                seen.add(identity)
            if len(selected) >= limit:
                break
        results = []
        for key in selected:
            passage = candidates[key]
            version = session.get(ReferenceVersion, passage.version_id)
            source = session.get(ReferenceSource, version.source_id)
            results.append(
                {
                    "passage_id": str(key),
                    "version_id": str(version.id),
                    "source_id": str(source.id),
                    "title": source.title,
                    "version": version.number,
                    "location": passage.location,
                    "content": passage.content,
                }
            )
        return results

    @staticmethod
    def validate_citations(session, citations):
        """Hold shared version locks through the caller's reply commit."""
        ids = {UUID(c["version_id"]) for c in citations}
        if not ids:
            return
        versions = session.scalars(
            select(ReferenceVersion)
            .where(ReferenceVersion.id.in_(ids))
            .order_by(ReferenceVersion.id)
            .with_for_update(read=True)
            .execution_options(populate_existing=True)
        ).all()
        if len(versions) != len(ids) or any(not v.active for v in versions):
            raise KnowledgeError("reference_conflict", 409)
