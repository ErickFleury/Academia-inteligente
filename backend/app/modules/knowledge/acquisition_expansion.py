"""Pinned, licensed JATS acquisition through the official Europe PMC full-text API."""

from __future__ import annotations

import argparse
import json
import re
import time
import xml.etree.ElementTree as ET
from datetime import UTC, date, datetime
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import HTTPRedirectHandler, Request, build_opener

from app.modules.knowledge.acquisition import (
    CACHE_PATH,
    CATALOG_PATH,
    AcquisitionError,
    digest,
    validate_packaged_source,
    write_json,
)

RECIPE_PATH = Path(__file__).with_name("acquisition-expansion.json")
EXTRACTOR = "europepmc-jats-selected-blocks/1"
MAX_BYTES = 10_000_000
ARTICLES = {
    "singer-rest-2024": "PMC11349676",
    "iversen-time-efficient-2021": "PMC8449772",
    "schumann-concurrent-2022": "PMC8891239",
    "ingram-stretch-mechanisms-2025": "PMC12152101",
    "smart-isometric-hypertension-2023": "PMC10015931",
    "su-diabetes-exercise-2026": "PMC13539497",
    "lafontant-body-fat-2025": "PMC12107660",
    "bao-depp-2026": "PMC13581003",
    "price-asthma-2025": "PMC12186601",
}
LICENSE_URL = "https://creativecommons.org/licenses/by/4.0/"


def article_url(pmc: str) -> str:
    if pmc not in ARTICLES.values():
        raise AcquisitionError("unapproved_article")
    return f"https://www.ebi.ac.uk/europepmc/webservices/rest/{pmc}/fullTextXML"


class NoRedirects(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise AcquisitionError("unapproved_redirect")


def download(pmc: str, *, opener=None, sleep=time.sleep) -> bytes:
    opener = opener or build_opener(NoRedirects())
    url = article_url(pmc)
    for attempt in range(2):
        try:
            with opener.open(
                Request(url, headers={"User-Agent": "AcademiaEvidence/1.0"}), timeout=30
            ) as response:
                if response.url != url:
                    raise AcquisitionError("unapproved_redirect")
                if response.headers.get_content_type() not in (
                    "application/xml",
                    "text/xml",
                    "application/jats+xml",
                ):
                    raise AcquisitionError("unexpected_content_type")
                body = response.read(MAX_BYTES + 1)
                if not body or len(body) > MAX_BYTES:
                    raise AcquisitionError("invalid_artifact_size")
                return body
        except HTTPError as error:
            if error.code not in (429, 500, 502, 503, 504) or attempt:
                raise AcquisitionError("download_http_failure") from error
            delay = error.headers.get("Retry-After", "2")
            if not delay.isdigit() or int(delay) > 30:
                raise AcquisitionError("download_retry_deferred") from error
            sleep(max(2, int(delay)))
        except (URLError, TimeoutError, OSError) as error:
            if attempt:
                raise AcquisitionError("download_unavailable") from error
            sleep(2)
    raise AcquisitionError("download_unavailable")


def plain(node: ET.Element) -> str:
    return " ".join("".join(node.itertext()).split())


def authors_from_metadata(meta: ET.Element) -> list[str]:
    authors = []
    for group in meta.findall("contrib-group"):
        if group.get("content-type") not in (None, "author"):
            continue
        for contrib in group.findall("contrib"):
            if contrib.get("contrib-type", "author") != "author":
                continue
            name = contrib.find("name")
            if name is not None:
                authors.append(
                    " ".join(filter(None, (name.findtext("given-names"), name.findtext("surname"))))
                )
    return authors


def prose(node: ET.Element) -> str:
    """Only author prose/lists: figures, tables, supplements and references omitted."""
    if node.tag in ("p", "title", "label"):
        return plain(node)
    if node.tag in ("fig", "table-wrap", "supplementary-material", "ref-list"):
        return ""
    return "\n\n".join(filter(None, (prose(child) for child in node)))


def selected_prose(node: ET.Element, selector: dict) -> str:
    if "block_indices" in selector:
        indexes = selector["block_indices"]
        blocks = [n for n in node if n.tag in ("p", "list")]
        if not indexes or any(type(i) is not int or i < 0 or i >= len(blocks) for i in indexes):
            raise AcquisitionError("invalid_block_selection")
        title = node.find("title")
        return "\n\n".join(
            ([plain(title)] if title is not None else []) + [prose(blocks[i]) for i in indexes]
        )
    indexes = selector.get("paragraph_indices")
    if indexes is None:
        return prose(node)
    paragraphs = node.findall("p")
    if (
        not indexes
        or len(set(indexes)) != len(indexes)
        or any(type(i) is not int or i < 0 or i >= len(paragraphs) for i in indexes)
    ):
        raise AcquisitionError("invalid_paragraph_selection")
    title = node.find("title")
    return "\n\n".join(
        ([plain(title)] if title is not None else []) + [prose(paragraphs[i]) for i in indexes]
    )


def table_text(table: ET.Element) -> str:
    """Keep cells, row/column spans, full headers, captions and footnotes together."""
    result = []
    for node in table:
        if node.tag in ("label", "caption", "table-wrap-foot"):
            result.append(prose(node))
        elif node.tag == "table":
            for row in node.findall(".//tr"):
                cells = []
                for cell in row:
                    spans = ",".join(
                        f"{key}={cell.get(key)}" for key in ("rowspan", "colspan") if cell.get(key)
                    )
                    cells.append((f"[{spans}] " if spans else "") + plain(cell))
                result.append(" | ".join(cells))
    return "\n".join(filter(None, result))


def read_article(body: bytes, entry: dict) -> tuple[ET.Element, str]:
    if not body or len(body) > MAX_BYTES or b"<!ENTITY" in body.upper():
        raise AcquisitionError("invalid_xml_artifact")
    try:
        root = ET.fromstring(body)
    except ET.ParseError as error:
        raise AcquisitionError("invalid_xml_artifact") from error
    meta = root.find("./front/article-meta")
    if meta is None:
        raise AcquisitionError("missing_article_metadata")
    title = meta.find("./title-group/article-title")
    if (
        meta.findtext("article-id[@pub-id-type='doi']") != entry["doi"]
        or (
            meta.findtext("article-id[@pub-id-type='pmcid']")
            or meta.findtext("article-id[@pub-id-type='pmc']")
        )
        not in (entry["pmc"], entry["pmc"].removeprefix("PMC"))
        or title is None
        or plain(title) != entry["source"]["title"]
        or not entry["source"]["authors"]
        or authors_from_metadata(meta) != entry["source"]["authors"]
    ):
        raise AcquisitionError("article_identity_mismatch")
    permissions = meta.find("permissions")
    if permissions is None:
        raise AcquisitionError("unverified_artifact_permission")
    rights = ET.tostring(permissions, encoding="unicode")
    links = [value for node in permissions.iter() for value in node.attrib.values()]
    if not any(value.replace("http://", "https://") == LICENSE_URL for value in links) or re.search(
        r"by-nc|by-nd|NonCommercial|NoDerivatives|Non-Commercial", rights, re.IGNORECASE
    ):
        raise AcquisitionError("unverified_artifact_permission")
    if entry["source"]["license"] != "CC-BY-4.0":
        raise AcquisitionError("unapproved_license")
    return root, rights


def extract(body: bytes, entry: dict) -> tuple[list[dict], str]:
    root, rights = read_article(body, entry)
    chunks, seen = [], set()
    for selection in entry["selections"]:
        blocks = []
        for selector in selection["selectors"]:
            tag = selector["tag"]
            if tag not in ("abstract", "sec", "table-wrap"):
                raise AcquisitionError("unapproved_extraction_selector")
            if tag == "abstract":
                nodes = [
                    n
                    for n in root.findall("./front/article-meta/abstract")
                    if not n.get("abstract-type")
                ]
            else:
                nodes = root.findall(f"./body//{tag}[@id='{selector['id']}']")
            if len(nodes) != 1:
                raise AcquisitionError("missing_or_ambiguous_extraction_section")
            node = nodes[0]
            content = table_text(node) if tag == "table-wrap" else selected_prose(node, selector)
            if not content.strip():
                raise AcquisitionError("empty_extraction_section")
            blocks.append(content)
        content = "\n\n".join(blocks)
        if len(content) > 11000 or digest(content.encode()) != selection["text_sha256"]:
            raise AcquisitionError("unreviewed_extraction_change")
        if content in seen:
            raise AcquisitionError("duplicate_extraction")
        seen.add(content)
        chunks.append({"id": selection["id"], "section": selection["locator"], "content": content})
    if not chunks:
        raise AcquisitionError("empty_extraction")
    return chunks, rights


def acquire(entry: dict, cache: Path, *, refresh=False, fetch=download) -> tuple[dict, dict]:
    source_id = entry["source"]["id"]
    if ARTICLES.get(source_id) != entry["pmc"]:
        raise AcquisitionError("unapproved_article")
    path = cache / f"{source_id}-manifest.json"
    if path.exists() and not refresh:
        previous = json.loads(path.read_text(encoding="utf-8"))
        hashed = previous["artifact_sha256"]
        if not re.fullmatch(r"[a-f0-9]{64}", hashed):
            raise AcquisitionError("invalid_cached_artifact_path")
        body = (cache / (hashed + ".xml")).read_bytes()
        if digest(body) != hashed:
            raise AcquisitionError("cached_artifact_integrity_failure")
        captured = previous["captured_at"]
    else:
        body, captured = fetch(entry["pmc"]), datetime.now(UTC).isoformat()
    chunks, rights = extract(body, entry)
    reviewed = entry["source"]
    if (
        reviewed["review_status"] != "approved"
        or not reviewed["commercial_use_allowed"]
        or not reviewed["reviewed_by"].strip()
        or not date.fromisoformat(reviewed["reviewed_at"])
        <= date.today()
        < date.fromisoformat(reviewed["review_due_at"])
    ):
        raise AcquisitionError("technical_review_not_current")
    hashed = digest(body)
    manifest = {
        "version": 1,
        "source_id": source_id,
        "identifier": "doi:" + entry["doi"],
        "repository_identifier": entry["pmc"],
        "article_version": entry["article_version"],
        "requested_url": article_url(entry["pmc"]),
        "final_url": article_url(entry["pmc"]),
        "captured_at": captured,
        "artifact_file": hashed + ".xml",
        "artifact_sha256": hashed,
        "artifact_bytes": len(body),
        "media_type": "application/xml",
        "extractor": EXTRACTOR,
        "license": reviewed["license"],
        "license_url": reviewed["license_url"],
        "license_evidence": rights,
        "license_evidence_sha256": digest(rights.encode()),
        "recipe_sha256": digest(json.dumps(entry, sort_keys=True).encode()),
        "scientific_approval": "pending",
        "chunks": [
            {"id": c["id"], "locator": c["section"], "text_sha256": digest(c["content"].encode())}
            for c in chunks
        ],
    }
    cache.mkdir(parents=True, exist_ok=True)
    original = cache / manifest["artifact_file"]
    temporary = original.with_suffix(".xml.tmp")
    temporary.write_bytes(body)
    temporary.replace(original)
    write_json(path, manifest)
    source = {**reviewed, "chunks": chunks, "captured_at": captured[:10], "provenance": manifest}
    validate_packaged_source(source)
    return source, manifest


def publish_batch(sources: list[dict], catalog_path: Path = CATALOG_PATH) -> None:
    """Publish only a complete validated batch; preserve every existing unrelated record."""
    if len({s["id"] for s in sources}) != len(sources):
        raise AcquisitionError("duplicate_catalog_source")
    for source in sources:
        if source["id"] not in ARTICLES:
            raise AcquisitionError("unapproved_article")
        validate_packaged_source(source)
    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    if len({s["id"] for s in catalog["sources"]}) != len(catalog["sources"]):
        raise AcquisitionError("duplicate_catalog_source")
    incoming = {s["id"]: s for s in sources}
    catalog["sources"] = [incoming.pop(s["id"], s) for s in catalog["sources"]]
    catalog["sources"].extend(incoming.values())
    write_json(catalog_path, catalog)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--refresh", action="store_true")
    parser.add_argument("--publish", action="store_true")
    args = parser.parse_args()
    recipe = json.loads(RECIPE_PATH.read_text(encoding="utf-8"))
    sources, manifests = [], []
    for entry in recipe["entries"]:
        source, manifest = acquire(entry, CACHE_PATH / "expansion", refresh=args.refresh)
        sources.append(source)
        manifests.append(manifest)
        print(json.dumps({"source_id": source["id"], "chunks": len(source["chunks"])}), flush=True)
        time.sleep(0.5)
    if args.publish:
        publish_batch(sources)
    write_json(
        CACHE_PATH / "expansion" / "acquisition.json",
        {"version": 1, "sources": manifests, "published": args.publish},
    )


if __name__ == "__main__":
    main()
