"""Reference lifecycle, bounded imports, and active-version-only retrieval."""

from __future__ import annotations

import math
import re
import unicodedata
from collections import Counter
from datetime import UTC, datetime, timedelta
from itertools import zip_longest
from uuid import UUID

from sqlalchemy import Float, Text, case, delete, func, literal_column, or_, select, text
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
from app.modules.knowledge.prescription_evidence import prescription_gaps, source_parameters
from app.modules.knowledge.search_terms import expand_search_terms


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


def exercise_heading(lines, index):
    """Read an explicit numbered exercise/video title, never infer it from prose."""
    if not re.fullmatch(
        r"(?:Video|Vídeo|Exercise|Exercício)\s+\d+(?:\.\d+)+", lines[index].strip()
    ):
        return ""
    title = []
    for line in lines[index + 1 : index + 5]:
        line = line.strip()
        if not line or re.fullmatch(r"\d+(?:\.\d+)+", line):
            continue
        if line.startswith(("Starting Position", "Posição Inicial")) or ":" in line:
            break
        words = re.findall(r"[\w]+", line)
        if (
            not words
            or len(line) > 140
            or line.endswith(".")
            or not all(
                word[0].isupper()
                or word.isdigit()
                or word in {"and", "of", "the", "for", "to", "with", "de", "com", "e"}
                for word in words
            )
        ):
            break
        title.append(line)
    return " ".join(title)[:280]


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
        for index, line in enumerate(lines):
            if re.fullmatch(
                r"\s*(?:(?:Part|Parte|Chapter|Capítulo)\s+(?:[IVXLCDM]+|\d+)"
                r"|(?i:About the [\w ]{1,60}|References|Bibliography|Index"
                r"|Referências|Bibliografia|Índice))\s*",
                line,
            ):
                if block:
                    yield page["location"], section, "\n".join(block)
                    block = []
                section = ""
            if title := exercise_heading(lines, index):
                if block:
                    yield page["location"], section, "\n".join(block)
                    block = []
                section = title
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
    words = {
        word.casefold()
        for page in pages
        for word in re.findall(r"[^\W\d_]+(?:-[^\W\d_]+)*", page["text"])
    }

    def unwrap(match):
        left, right = match.groups()
        compound = f"{left}-{right}"
        # Only remove a hyphen when the document supplies the intact spelling.
        # Otherwise retain it: five-point and single-joint are meaningful terms.
        joined = left + right
        return (
            joined if joined.casefold() in words and compound.casefold() not in words else compound
        )

    position = 0
    for location, section, block in section_blocks(pages):
        prefix = f"Seção: {section}\n" if section else ""
        if location.startswith("page:"):
            block = re.sub(r"([^\W\d_]+)-[ \t]*\n[ \t]*([a-zà-ÿ]+)", unwrap, block)
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
    words = words - {
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
    return {
        "jovem" if word == "jovens" else word[:-1] if len(word) > 3 and word.endswith("s") else word
        for word in words
    }


def section_match(content, query):
    if not content.startswith("Seção: "):
        return 0
    heading = content.split("\n", 1)[0][7:]
    return len(section_terms(heading) & section_terms(query))


_TECHNIQUE_MARKERS = (
    "starting position",
    "backward movement",
    "forward movement",
    "upward movement",
    "downward movement",
    "pushing movement",
    "pulling movement",
    "posição inicial",
    "fase concêntrica",
    "fase excêntrica",
    "execução do movimento",
)


def technique_passage(content):
    """Recognize explicit execution sections, not generic benefits or definitions.

    This is a retrieval hint only. Applicability, exercise variants and quantities
    still require the independent prescription and model checks.
    """
    if not content.startswith("Seção: "):
        return False
    body = content.partition("\n")[2].casefold()
    return any(marker in body for marker in _TECHNIQUE_MARKERS)


def technique_subject_terms(content):
    """A technique promotion must match a subject, not a generic chapter label."""
    heading = content.split("\n", 1)[0][7:].rsplit(" / ", 1)[-1]
    generic = section_terms(
        "training resistance strength technique execution exercise movement programming "
        "treinamento musculação força técnica execução exercício movimento programação "
        "starting position posição inicial beginner novice adult iniciante adulto"
    )
    return section_terms(heading) - generic


def technique_subject_match(content, query):
    return len(technique_subject_terms(content) & section_terms(query))


def unusable_table(content):
    """Exclude clearly broken numeric layouts, never reconstruct their doses.

    A conservative retrieval guard, not an OCR accuracy score. Preserve prose,
    labelled rows and structured Markdown tables; retain the original in storage.
    """
    if not re.search(r"\b(?:table|tabela)\b", content, re.I):
        return False
    lines = [line.strip() for line in content.splitlines() if line.strip()]
    if len(lines) < 8:
        return False
    if any(re.fullmatch(r"\|?\s*:?-{3,}:?\s*(?:\|\s*:?-{3,}:?\s*)+\|?", line) for line in lines):
        return False
    opaque = sum(
        bool(re.search(r"\d", line)) and not re.search(r"[^\W\d_]{3,}", line) for line in lines
    )
    return opaque >= 6 and opaque / len(lines) >= 0.45


def distinct_technique_rows(rows, *, limit=20):
    selected, seen = [], set()
    for row in rows:
        heading = row.content.split("\n", 1)[0].casefold()
        if heading not in seen and technique_passage(row.content):
            selected.append(row)
            seen.add(heading)
        if len(selected) == limit:
            break
    return selected


def merge_plan_references(additional, previous, *, limit=5):
    """Preserve complementary evidence within the caller's bounded context.

    Keep each search's leading result and use remaining slots for missing evidence
    types before redundant background. These are coverage hints, not assertions
    that quantities apply to an exercise/client. Preserve full text and rank order
    so conditions and provenance remain available to semantic review.
    """
    if not 1 <= limit <= 12:
        raise KnowledgeError("reference_query_invalid")
    ordered, seen = [], set()
    for pair in zip_longest(additional, previous):
        for reference in pair:
            if reference and reference["passage_id"] not in seen:
                ordered.append(reference)
                seen.add(reference["passage_id"])
    if len(ordered) <= limit or limit == 1:
        return ordered[:limit]
    facets = {}
    for reference, parameters in zip(ordered, source_parameters(ordered), strict=True):
        kinds = {
            key
            for key in ("sets", "repetitions", "rest_seconds", "duration_seconds", "weekly_seconds")
            if parameters[key]
        }
        kinds.update(f"activity:{name}" for name in parameters["named_activities"])
        if technique_passage(reference["content"]):
            kinds.add("technique")
            kinds.add(
                "technique:" + " ".join(sorted(technique_subject_terms(reference["content"])))
            )
        if re.search(r"dividir|distribu|spread|divide", reference["content"], re.I):
            kinds.add("distribution")
        facets[reference["passage_id"]] = kinds
    selected = {ranking[0]["passage_id"] for ranking in (additional, previous) if ranking}
    covered = set().union(*(facets[key] for key in selected))
    remaining = [reference for reference in ordered if reference["passage_id"] not in selected]
    while len(selected) < limit and remaining:
        # max preserves the existing rank order on equal coverage gains.
        best = max(remaining, key=lambda row: len(facets[row["passage_id"]] - covered))
        selected.add(best["passage_id"])
        covered.update(facets[best["passage_id"]])
        remaining.remove(best)
    return [reference for reference in ordered if reference["passage_id"] in selected]


def measurement_terms(query):
    """Recall measurement-bearing passages when repeated headings dominate overlap."""
    terms = section_terms(query)
    if terms & {"minuto", "hora", "tempo", "duracao", "segundo", "minute", "duration"}:
        return "minuto hora segundo minute hour second"
    if terms & {
        "frequencia",
        "freq",
        "dia",
        "semana",
        "vez",
        "veze",
        "frequency",
        "weekly",
        "week",
        "set",
        "serie",
    }:
        return "dia semana vez day week weekly wk session set"
    if terms & {"carga", "quilo", "kg", "quilograma"}:
        return "quilo kg quilograma"
    return ""


def bibliography_weight(content):
    # A list of papers often repeats the question's vocabulary but supplies no
    # guidance. Downrank multiple journal year/volume citations, never delete it.
    return 0.2 if len(re.findall(r"\b(?:19|20)\d{2};\s*\d+", content)) >= 2 else 1.0


def prescription_weight(content, query):
    """Prefer measured guidance for dose searches, without treating it as approval."""
    terms = section_terms(query)
    if terms & {"definition", "definicao", "significa", "conceito"}:
        return 1.0
    dose_terms = {
        "serie",
        "set",
        "repeticao",
        "repetition",
        "rep",
        "descanso",
        "rest",
        "intensidade",
        "intensity",
        "frequencia",
        "frequency",
        "duracao",
        "duration",
    }
    if not terms & {"prescription", "prescricao"} and len(terms & dose_terms) < 2:
        return 1.0
    measures = re.findall(
        r"\d+(?:[–−-]\d+)?\s*(?:sets?\b|séries?\b|repeti(?:tions|ções)\b|"
        r"minutes?\b|minutos?\b|seconds?\b|segundos?\b|sessions?\b|dias?\b|%\s*1\s*RM)",
        content,
        re.I,
    )
    return 1 + 0.05 * min(3, len(measures))


def population_weight(content, query):
    """Downrank explicit mismatches, including unlabelled PDF prose.

    This is a soft relevance hint, not a clinical applicability verdict. Mixed
    populations and unknown scope remain available to the specialist/reviewer.
    """
    patterns = {
        "older": (
            r"\b(?:older|elderly)\s+(?:adults?|clients?|men|women|people|persons?)\b"
            r"|\bidos[oa]s?\b"
        ),
        "youth": (
            r"\b(?:children|child|youth|adolescents?|criancas?|adolescentes?)\b"
            r"|\bjovens?\b(?!\s+adult)"
        ),
        "pregnancy": r"\b(?:pregnant|pregnancy|gestantes?|posparto)\b",
        "disability": r"\b(?:disabilit\w*|deficiencia\w*)\b",
    }

    def scope(value):
        value = "".join(
            char
            for char in unicodedata.normalize("NFKD", value.casefold())
            if not unicodedata.combining(char)
        )
        tags = set()
        for tag, pattern in patterns.items():
            if re.search(pattern, value):
                tags.add(tag)
                value = re.sub(pattern, " ", value)
        if re.search(r"\badult[oa]?s?\b", value):
            tags.add("adult")
        return tags

    wanted, described = scope(query), scope(content)
    # "Older adults" is a specific population, not a general-adult match.
    if wanted and described and not wanted & described:
        return 0.25
    novice = {"beginner", "novice", "untrained", "iniciante", "destreinado"}
    advanced = {
        "advanced",
        "experienced",
        "avancado",
        "experiente",
        "elite",
        "intermediate",
        "intermediario",
    }
    query_terms, content_terms = section_terms(query), section_terms(content)
    if query_terms & novice and not content_terms & novice:
        if content_terms & (advanced | {"athlete", "atleta", "competition", "competicao"}):
            return 0.25
    return 1.0


class KnowledgeService:
    prescription_gaps = staticmethod(prescription_gaps)

    def __init__(self, provider: EmbeddingProvider | None = None):
        self.provider = provider or HttpEmbeddingProvider()

    def expand_plan_context(self, session, references, *, limit=12):
        """Attach adjacent source text after an explicit plan-evidence gap.

        This is bounded context around retrieved passages, not another semantic
        search. Keep full provenance and applicability conditions for review.
        """
        if not 1 <= limit <= 12 or len(references) > limit:
            raise KnowledgeError("reference_query_invalid")
        if not references or len(references) == limit:
            return references
        by_id = {UUID(ref["passage_id"]): ref for ref in references}
        seeds = session.scalars(
            select(ReferencePassage)
            .join(ReferenceVersion)
            .where(
                ReferencePassage.id.in_(by_id),
                ReferenceVersion.active.is_(True),
                ReferenceVersion.status == "active",
            )
        ).all()
        if len(seeds) != len(by_id):
            raise KnowledgeError("reference_conflict", 409)
        order = {key: index for index, key in enumerate(by_id)}
        seeds.sort(key=lambda seed: order[seed.id])
        links = []
        for seed in seeds:
            numbers = re.findall(
                r"\b(?:based on|see|conforme|ver|and|e|basead[oa]s? n[ao])\s+"
                r"(?:table|tabela)\s+(\d{1,3}\.\d{1,3})\b",
                seed.content,
                re.I,
            ) + re.findall(
                r"(?im)^\s*(?:#{1,6}\s*)?(?:table|tabela)\s+(\d{1,3}\.\d{1,3})"
                r"\s*\((?:continued|continua[çc][ãa]o)\)",
                seed.content,
            )
            for number in numbers:
                if not any(
                    item[0].version_id == seed.version_id and item[1] == number for item in links
                ):
                    links.append((seed, number))
                if len(links) == 4:
                    break
            if len(links) == 4:
                break
        result, seen, tables = list(references), set(by_id), []
        if links:
            linked = session.scalars(
                select(ReferencePassage)
                .join(ReferenceVersion)
                .where(
                    ReferenceVersion.active.is_(True),
                    ReferenceVersion.status == "active",
                    or_(
                        *[
                            (ReferencePassage.version_id == seed.version_id)
                            & or_(
                                ReferencePassage.content.ilike(f"%table {number}%"),
                                ReferencePassage.content.ilike(f"%tabela {number}%"),
                            )
                            for seed, number in links
                        ]
                    ),
                )
                .order_by(ReferencePassage.position, ReferencePassage.id)
                .limit(24)
            ).all()
            for seed, number in links:
                for row in linked:
                    if (
                        row.version_id != seed.version_id
                        or row.id in seen
                        or unusable_table(row.content)
                        or not re.search(
                            r"(?im)^\s*(?:#{1,6}\s*)?(?:table|tabela)\s+"
                            + re.escape(number)
                            + r"\b(?!\s+(?:presents?|shows?|provides?|summarizes?|"
                            r"apresenta|mostra|resume)\b)",
                            row.content,
                        )
                    ):
                        continue
                    result.append(
                        {
                            **by_id[seed.id],
                            "passage_id": str(row.id),
                            "location": row.location,
                            "content": row.content,
                        }
                    )
                    seen.add(row.id)
                    tables.append((seed, number, row))
                    if len(result) == limit:
                        return result
                    break
            # A table's nearby introduction may qualify when its numbers apply.
            # Reuse bounded lookup candidates; follow explicit mentions only
            # within two positions of the actual table in the same version.
            for seed, number, table in tables:
                for row in linked:
                    if (
                        row.version_id != table.version_id
                        or row.id in seen
                        or not 0 < table.position - row.position <= 2
                        or unusable_table(row.content)
                        or not re.search(
                            r"\b(?:table|tabela)\s+" + re.escape(number) + r"\b",
                            row.content,
                            re.I,
                        )
                    ):
                        continue
                    result.append(
                        {
                            **by_id[seed.id],
                            "passage_id": str(row.id),
                            "location": row.location,
                            "content": row.content,
                        }
                    )
                    seen.add(row.id)
                    if len(result) == limit:
                        return result
        nearby = session.scalars(
            select(ReferencePassage)
            .join(ReferenceVersion)
            .where(
                ReferenceVersion.active.is_(True),
                ReferenceVersion.status == "active",
                or_(
                    *[
                        (ReferencePassage.version_id == seed.version_id)
                        & ReferencePassage.position.in_([seed.position - 1, seed.position + 1])
                        for seed in seeds
                    ]
                ),
            )
        ).all()
        neighbors = {(row.version_id, row.position): row for row in nearby}

        def continued(seed):
            return bool(re.search(r"\bcontinued\b|\bcontinua[çc][ãa]o\b", seed.content[:100], re.I))

        seeds.sort(key=lambda seed: (not continued(seed), order[seed.id]))
        for seed in seeds:
            for delta in (-1, 1) if continued(seed) else (1, -1):
                row = neighbors.get((seed.version_id, seed.position + delta))
                if row is None or row.id in seen or unusable_table(row.content):
                    continue
                seed_page = re.match(r"page:(\d+)", seed.location)
                row_page = re.match(r"page:(\d+)", row.location)
                if seed_page and row_page and abs(int(seed_page[1]) - int(row_page[1])) > 1:
                    continue
                result.append(
                    {
                        **by_id[seed.id],
                        "passage_id": str(row.id),
                        "location": row.location,
                        "content": row.content,
                    }
                )
                seen.add(row.id)
                if len(result) == limit:
                    return result
        return result

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
            source = session.get(ReferenceSource, source_id, populate_existing=True)
            if source is None:
                raise KnowledgeError("reference_not_found", 404)
            # Adding a version changes the scope of a source-wide deletion.
            source.revision += 1
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

    def delete_source(self, session, source_id, revision):
        """Erase uploaded bytes and every derived version, serialized with imports/citations."""
        catalog_lock(session)
        source = session.scalar(
            select(ReferenceSource)
            .where(ReferenceSource.id == source_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        if source is None:
            raise KnowledgeError("reference_not_found", 404)
        if source.revision != revision:
            raise KnowledgeError("reference_conflict", 409)
        version_ids = list(
            session.scalars(
                select(ReferenceVersion.id)
                .where(ReferenceVersion.source_id == source_id)
                .order_by(ReferenceVersion.id)
                .with_for_update()
            )
        )
        session.execute(
            delete(ReferencePassage).where(ReferencePassage.version_id.in_(version_ids))
        )
        session.execute(delete(ReferenceVersion).where(ReferenceVersion.source_id == source_id))
        session.delete(source)
        session.commit()
        # A worker embedding outside the transaction observes the missing version
        # before inserting its next batch. Citation validation rejects missing IDs.

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

    def search(
        self,
        session: Session,
        query: str,
        *,
        timeout: float = 10,
        limit: int = 5,
        include_activity_options: bool = False,
        prefer_technique: bool = False,
    ):
        if not query.strip() or len(query) > 500 or not 1 <= limit <= 10:
            raise KnowledgeError("reference_query_invalid")
        query = expand_search_terms(query)
        technique_focus = prefer_technique and bool(
            section_terms(query) & {"technique", "tecnica", "execucao", "execution", "movement"}
        )
        technique_filter = (
            ReferencePassage.content.startswith("Seção: "),
            or_(*(ReferencePassage.content.ilike(f"%{marker}%") for marker in _TECHNIQUE_MARKERS)),
        )
        base = (
            select(ReferencePassage)
            .join(ReferenceVersion)
            .where(ReferenceVersion.active.is_(True), ReferenceVersion.status == "active")
        )

        def technique_candidates(statement, relevance):
            # Diversity must happen before LIMIT: otherwise repeated pages of
            # one exercise consume the entire focused candidate pool.
            grouped = statement.with_only_columns(
                ReferencePassage.id.label("passage_id"),
                relevance.label("relevance"),
                func.row_number()
                .over(
                    partition_by=func.split_part(ReferencePassage.content, "\n", 1),
                    order_by=(relevance, ReferenceVersion.source_id, ReferencePassage.position),
                )
                .label("subject_rank"),
            ).subquery()
            return session.scalars(
                select(ReferencePassage)
                .join(grouped, grouped.c.passage_id == ReferencePassage.id)
                .where(grouped.c.subject_rank == 1)
                .order_by(grouped.c.relevance, ReferencePassage.position, ReferencePassage.id)
                .limit(20)
            ).all()

        focused, technique_lexical, technique_semantic = [], [], []
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
                .order_by(
                    func.ts_rank_cd(document, terms).desc(),
                    ReferenceVersion.source_id,
                    ReferencePassage.position,
                )
                .limit(20)
            ).all()
            if technique_focus:
                technique_lexical = technique_candidates(
                    base.where(document.op("@@")(terms), *technique_filter),
                    -func.ts_rank_cd(document, terms),
                )
            if units := measurement_terms(query):
                unit_query = func.plainto_tsquery(text("'portuguese'::regconfig"), units)
                unit_terms = func.replace(unit_query.cast(Text), " & ", " | ").cast(TSQUERY)
                focused = session.scalars(
                    base.where(document.op("@@")(terms), document.op("@@")(unit_terms))
                    .order_by(
                        func.ts_rank_cd(document, terms).desc(),
                        ReferenceVersion.source_id,
                        ReferencePassage.position,
                    )
                    .limit(20)
                ).all()
        else:
            # SQLite is only the deterministic unit-test dialect; production uses PostgreSQL.
            terms = set(re.findall(r"\w+", query.casefold()))
            rows = session.scalars(base).all()
            lexical_candidates = sorted(
                (r for r in rows if terms & set(re.findall(r"\w+", r.content.casefold()))),
                key=lambda r: -len(terms & set(re.findall(r"\w+", r.content.casefold()))),
            )
            lexical = lexical_candidates[:20]
            if technique_focus:
                technique_lexical = distinct_technique_rows(lexical_candidates)
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
                    compatible.where(distance <= 0.60)
                    .order_by(distance, ReferenceVersion.source_id, ReferencePassage.position)
                    .limit(20)
                ).all()
                if technique_focus:
                    # Reuse the same query vector and distance threshold. An
                    # execution passage must survive candidate selection even
                    # when twenty programming passages rank ahead of it.
                    technique_semantic = technique_candidates(
                        compatible.where(distance <= 0.60, *technique_filter), distance
                    )
            else:

                def distance(row):
                    a, b = row.embedding, query_vector
                    return 1 - sum(x * y for x, y in zip(a, b, strict=True)) / (
                        math.sqrt(sum(x * x for x in a)) * math.sqrt(sum(y * y for y in b))
                    )

                semantic_candidates = sorted(
                    (r for r in session.scalars(compatible) if distance(r) <= 0.60), key=distance
                )
                semantic = semantic_candidates[:20]
                if technique_focus:
                    technique_semantic = distinct_technique_rows(semantic_candidates)
        except AiProviderError:
            pass  # Explicit lexical-only degradation; never switch provider.
        semantic_ranks = {}
        previous_distance, tied_rank = None, 1
        for rank, passage in enumerate(semantic, 1):
            vector = passage.embedding
            value = 1 - sum(a * b for a, b in zip(vector, query_vector, strict=True)) / (
                math.sqrt(sum(a * a for a in vector)) * math.sqrt(sum(b * b for b in query_vector))
            )
            if previous_distance is None or not math.isclose(
                value, previous_distance, abs_tol=1e-7
            ):
                tied_rank = rank
            semantic_ranks[passage.id] = tied_rank
            previous_distance = value
        scores, candidates = {}, {}
        # Preserve meaningful semantic rank differences. Measurement candidates
        # broaden recall, but their numerical density must not overwhelm topic
        # relevance. Heading/dose bonuses below are deliberately small.
        for ranking, weight in (
            (lexical, 1),
            (semantic, 4),
            (focused, 0.5 if semantic else 2),
            (technique_lexical, 1),
            (technique_semantic, 1),
        ):
            for rank, passage in enumerate(ranking, 1):
                if unusable_table(passage.content):
                    continue
                if ranking is semantic:
                    rank = semantic_ranks[passage.id]
                candidates[passage.id] = passage
                scores[passage.id] = scores.get(passage.id, 0) + weight / (10 + rank)
        # Heading matches boost applicability without filtering out conflicting
        # evidence from other sources or relying on inferred personal attributes.
        ranked = sorted(
            scores,
            key=lambda key: (
                -(
                    scores[key]
                    * (1 + 0.05 * min(3, section_match(candidates[key].content, query)))
                    * bibliography_weight(candidates[key].content)
                    * prescription_weight(candidates[key].content, query)
                    * population_weight(candidates[key].content, query)
                ),
                candidates[key].position,
                str(candidates[key].version_id),
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
        if include_activity_options and limit >= 3:

            def has_activity(key):
                return bool(
                    source_parameters(
                        [{"passage_id": str(key), "content": candidates[key].content}]
                    )[0]["named_activities"]
                )

            if not any(has_activity(key) for key in selected[:3]):
                candidate = next(
                    (
                        key
                        for key in ranked
                        if has_activity(key)
                        and population_weight(candidates[key].content, query) == 1
                    ),
                    None,
                )
                if candidate is not None:
                    selected = [key for key in selected if key != candidate]
                    selected.insert(min(2, len(selected)), candidate)
                    selected = selected[:limit]
        if technique_focus:
            # The complementary search must not return only another set of
            # programming abstracts. Promote a relevant execution passage from
            # the SAME bounded candidate pool; never fetch a random exercise or
            # impose a source quota. Preserve ordinary ranking for other slots.
            matches = [
                key
                for key in ranked
                if technique_passage(candidates[key].content)
                and population_weight(candidates[key].content, query) == 1
                and technique_subject_match(candidates[key].content, query) > 0
            ]
            covered, diverse = set(), []
            subjects = {
                key: technique_subject_terms(candidates[key].content) & section_terms(query)
                for key in matches
            }
            while matches and len(diverse) < limit:
                candidate = max(matches, key=lambda key: len(subjects[key] - covered))
                if not subjects[candidate] - covered:
                    break
                diverse.append(candidate)
                covered.update(subjects[candidate])
                matches.remove(candidate)
            selected = [*diverse, *(key for key in selected if key not in diverse)][:limit]
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
