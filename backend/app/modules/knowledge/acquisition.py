"""Bounded S4 acquisition; reviewed selections only, never a general URL fetcher."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from datetime import UTC, date, datetime
from html.parser import HTMLParser
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

SOURCE_ID = "lyristakis-strength-2026"
CATALOG_PATH = Path(__file__).with_name("catalog.json")
ARTICLE_URL = "https://link.springer.com/article/10.1007/s40279-026-02432-5"
RECIPE_PATH = Path(__file__).with_name("acquisition-s4.json")
PROVENANCE_REQUIRED = frozenset(
    (
        SOURCE_ID,
        "singer-rest-2024",
        "iversen-time-efficient-2021",
        "schumann-concurrent-2022",
        "ingram-stretch-mechanisms-2025",
        "smart-isometric-hypertension-2023",
        "su-diabetes-exercise-2026",
        "lafontant-body-fat-2025",
        "bao-depp-2026",
        "price-asthma-2025",
    )
)
CACHE_PATH = Path(__file__).resolve().parents[3] / ".cache" / "training-evidence"
MAX_BYTES = 5_000_000
EXTRACTOR_VERSION = "springer-heading-paragraphs/1"
ALLOWED_PATH = "/article/10.1007/s40279-026-02432-5"


class AcquisitionError(ValueError):
    """Controlled acquisition/quarantine failure, without document content."""


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def allowed_url(url: str) -> bool:
    value = urlsplit(url)
    return (
        value.scheme == "https"
        and value.hostname in ("link.springer.com", "link.springernature.com")
        and value.port in (None, 443)
        and value.username is None
        and value.password is None
        and value.path == ALLOWED_PATH
    )


class ArticleRedirects(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        value = urlsplit(newurl)
        # The official public article uses these two publisher cookie-handshake
        # routes. No credentials/cookies are supplied; final response must be the article.
        handshake = (
            value.scheme == "https"
            and value.hostname == "idp.springer.com"
            and value.path in ("/authorize", "/transit")
            and value.port in (None, 443)
            and value.username is None
            and value.password is None
        )
        if not (allowed_url(newurl) or handshake):
            raise AcquisitionError("unapproved_redirect")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def download(*, opener=None, sleep=time.sleep) -> tuple[bytes, str]:
    """One request at a time, at most one retry, no access-control bypass."""
    opener = opener or build_opener(ArticleRedirects())
    for attempt in range(2):
        try:
            request = Request(ARTICLE_URL, headers={"User-Agent": "AcademiaEvidence/1.0"})
            with opener.open(request, timeout=30) as response:
                if not allowed_url(response.url):
                    raise AcquisitionError("unapproved_redirect")
                if response.headers.get_content_type() != "text/html":
                    raise AcquisitionError("unexpected_content_type")
                body = response.read(MAX_BYTES + 1)
                if not body or len(body) > MAX_BYTES:
                    raise AcquisitionError("invalid_artifact_size")
                final = urlsplit(response.url)
                return body, f"{final.scheme}://{final.netloc}{final.path}"
        except HTTPError as error:
            if error.code not in (429, 500, 502, 503, 504) or attempt:
                raise AcquisitionError("download_http_failure") from error
            # Do not retry sooner than Retry-After; defer rather than wait unboundedly.
            delay = error.headers.get("Retry-After", "2")
            if not delay.isdigit() or int(delay) > 30:
                raise AcquisitionError("download_retry_deferred") from error
            sleep(max(2, int(delay)))
        except (URLError, TimeoutError, OSError) as error:
            if attempt:
                raise AcquisitionError("download_unavailable") from error
            sleep(2)
    raise AcquisitionError("download_unavailable")


class ArticleParagraphs(HTMLParser):
    """Extract paragraphs by publisher heading ID; no tables, scripts or media."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.heading: str | None = None
        self.paragraph: list[str] | None = None
        self.sections: dict[str, list[str]] = {}
        self.ignored = 0

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self.ignored += 1
        if tag in ("h1", "h2", "h3", "h4"):
            self.heading = dict(attrs).get("id")
        if tag == "p" and self.heading and not self.ignored:
            self.paragraph = []

    def handle_endtag(self, tag):
        if tag in ("script", "style"):
            self.ignored = max(0, self.ignored - 1)
        if tag == "p" and self.paragraph is not None:
            self.sections.setdefault(self.heading, []).append(
                " ".join("".join(self.paragraph).split())
            )
            self.paragraph = None

    def handle_data(self, data):
        if self.paragraph is not None and not self.ignored:
            self.paragraph.append(data)


def extract(body: bytes, recipe: dict) -> tuple[list[dict], str]:
    if recipe["source"]["license"] != "CC-BY-4.0":
        raise AcquisitionError("unapproved_license")
    parser = ArticleParagraphs()
    try:
        parser.feed(body.decode("utf-8", errors="strict"))
    except UnicodeError as error:
        raise AcquisitionError("invalid_encoding") from error
    rights = "\n".join(parser.sections.get("rightslink", []))
    if (
        "Creative Commons Attribution 4.0 International License" not in rights
        or "creativecommons.org/licenses/by/4.0/" not in rights
        or "third party material" not in rights
        or "NonCommercial" in rights
        or "NoDerivatives" in rights
    ):
        raise AcquisitionError("unverified_artifact_permission")
    chunks = []
    for selection in recipe["selections"]:
        paragraphs = []
        for heading in selection["heading_ids"]:
            values = parser.sections.get(heading, [])
            if not values or any(not value for value in values):
                raise AcquisitionError("missing_extraction_section")
            paragraphs.extend(values)
        content = "\n\n".join(paragraphs)
        if len(content) > 11000 or digest(content.encode()) != selection["text_sha256"]:
            raise AcquisitionError("unreviewed_extraction_change")
        chunks.append({"id": selection["id"], "section": selection["locator"], "content": content})
    if len({chunk["content"] for chunk in chunks}) != len(chunks):
        raise AcquisitionError("duplicate_extraction")
    return chunks, rights


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def acquire(cache: Path, recipe: dict, *, refresh=False) -> tuple[dict, dict]:
    manifest_path = cache / "s4-manifest.json"
    if not refresh and manifest_path.exists():
        previous = json.loads(manifest_path.read_text(encoding="utf-8"))
        expected_file = previous["artifact_sha256"] + ".html"
        if (
            previous["artifact_file"] != expected_file
            or len(previous["artifact_sha256"]) != 64
            or any(c not in "0123456789abcdef" for c in previous["artifact_sha256"])
        ):
            raise AcquisitionError("invalid_cached_artifact_path")
        body = (cache / previous["artifact_file"]).read_bytes()
        if digest(body) != previous["artifact_sha256"]:
            raise AcquisitionError("cached_artifact_integrity_failure")
        final_url, captured = previous["final_url"], previous["captured_at"]
        if not allowed_url(final_url):
            raise AcquisitionError("unapproved_cached_url")
    else:
        body, final_url = download()
        captured = datetime.now(UTC).isoformat()
    # Extraction/permission failures leave the previous manifest and catalog intact.
    chunks, rights = extract(body, recipe)
    reviewed = recipe["source"]
    if (
        reviewed["review_status"] != "approved"
        or not reviewed["commercial_use_allowed"]
        or not reviewed["reviewed_by"].strip()
        or not date.fromisoformat(reviewed["reviewed_at"])
        <= date.today()
        < date.fromisoformat(reviewed["review_due_at"])
    ):
        raise AcquisitionError("technical_review_not_current")
    artifact_hash = digest(body)
    manifest = {
        "version": 1,
        "source_id": SOURCE_ID,
        "identifier": recipe["identifier"],
        "article_version": "2026-04-17",
        "requested_url": ARTICLE_URL,
        "final_url": final_url,
        "captured_at": captured,
        "artifact_file": artifact_hash + ".html",
        "artifact_sha256": artifact_hash,
        "artifact_bytes": len(body),
        "media_type": "text/html",
        "extractor": EXTRACTOR_VERSION,
        "python_version": sys.version.split()[0],
        "license": reviewed["license"],
        "license_url": reviewed["license_url"],
        "license_evidence": rights,
        "license_evidence_sha256": digest(rights.encode()),
        "recipe_sha256": digest(json.dumps(recipe, sort_keys=True).encode()),
        "scientific_approval": "pending",
        "chunks": [
            {"id": c["id"], "locator": c["section"], "text_sha256": digest(c["content"].encode())}
            for c in chunks
        ],
    }
    cache.mkdir(parents=True, exist_ok=True)
    artifact_path = cache / manifest["artifact_file"]
    temporary = artifact_path.with_suffix(".html.tmp")
    temporary.write_bytes(body)
    temporary.replace(artifact_path)
    write_json(manifest_path, manifest)
    source = {**reviewed, "chunks": chunks, "captured_at": captured[:10], "provenance": manifest}
    source["content_note"] += f" Original HTML SHA-256: {artifact_hash}."
    return source, manifest


def publish(source: dict, catalog_path: Path = CATALOG_PATH) -> None:
    validate_packaged_source(source)
    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    entries = catalog["sources"]
    positions = [index for index, entry in enumerate(entries) if entry["id"] == SOURCE_ID]
    if len(positions) > 1:
        raise AcquisitionError("duplicate_catalog_source")
    if positions:
        entries[positions[0]] = source
    else:
        entries.append(source)
    write_json(catalog_path, catalog)


def validate_packaged_source(source: dict) -> None:
    """Fail closed on a changed selection/provenance before requesting embeddings."""
    provenance = source.get("provenance")
    if not provenance:
        if source["id"] in PROVENANCE_REQUIRED:
            raise AcquisitionError("missing_artifact_provenance")
        return  # Legacy seed sources retain their existing review contract.
    if provenance["source_id"] != source["id"] or provenance["license"] != source["license"]:
        raise AcquisitionError("source_provenance_mismatch")
    if (
        len(provenance["artifact_sha256"]) != 64
        or any(c not in "0123456789abcdef" for c in provenance["artifact_sha256"])
        or digest(provenance["license_evidence"].encode()) != provenance["license_evidence_sha256"]
    ):
        raise AcquisitionError("invalid_provenance_integrity")
    recorded = {chunk["id"]: chunk for chunk in provenance["chunks"]}
    if len(recorded) != len(source["chunks"]):
        raise AcquisitionError("extraction_manifest_mismatch")
    for chunk in source["chunks"]:
        expected = recorded.get(chunk["id"], {})
        if (
            expected.get("text_sha256") != digest(chunk["content"].encode())
            or expected.get("locator") != chunk["section"]
        ):
            raise AcquisitionError("extraction_manifest_mismatch")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--refresh", action="store_true", help="Recheck the official article")
    parser.add_argument("--publish", action="store_true", help="Package matching reviewed text")
    args = parser.parse_args()
    recipe = json.loads(RECIPE_PATH.read_text(encoding="utf-8"))
    try:
        source, manifest = acquire(CACHE_PATH, recipe, refresh=args.refresh)
        if args.publish:
            publish(source)
        print(
            json.dumps(
                {
                    "source_id": SOURCE_ID,
                    "chunks": len(source["chunks"]),
                    "artifact_sha256": manifest["artifact_sha256"],
                    "published": args.publish,
                }
            )
        )
    except (AcquisitionError, OSError, ValueError, KeyError) as error:
        raise SystemExit(f"Acquisition incomplete: {type(error).__name__}: {error}") from error


if __name__ == "__main__":
    main()
