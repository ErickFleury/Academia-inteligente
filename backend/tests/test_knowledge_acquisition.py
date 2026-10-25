"""Offline acquisition, provenance and rollback checks; no external services."""

import copy
import json
from email.message import Message
from io import BytesIO
from urllib.error import HTTPError
from urllib.request import Request

import pytest
from sqlalchemy import select
from test_knowledge import FakeEmbeddings, catalog_source
from test_training_generation import session as session

from app.modules.knowledge import acquisition as acquisition
from app.modules.knowledge.bootstrap import seed_catalog
from app.modules.knowledge.models import KnowledgeChunk


@pytest.fixture
def article():
    recipe = json.loads(acquisition.RECIPE_PATH.read_text(encoding="utf-8"))
    recipe["selections"] = [
        {
            "id": acquisition.SOURCE_ID + "-test",
            "heading_ids": ["Sec5", "Sec15"],
            "locator": "2.2; 5",
            "text_sha256": acquisition.digest(b"Adults only.\n\nNot causal."),
        }
    ]
    body = b"""<h3 id="Sec5">Eligibility</h3><p>Adults only.</p>
    <h2 id="Sec15">Limitations</h2><p>Not causal.</p>
    <h2 id="rightslink">Rights</h2><p>Creative Commons Attribution 4.0 International License
    http://creativecommons.org/licenses/by/4.0/ except third party material.</p>"""
    return body, recipe


class Response(BytesIO):
    url = acquisition.ARTICLE_URL

    def __init__(self, data, content_type="text/html"):
        super().__init__(data)
        self.headers = Message()
        self.headers["Content-Type"] = content_type


class Opener:
    def __init__(self, *responses):
        self.responses = iter(responses)
        self.calls = 0

    def open(self, request, *, timeout):
        assert request.full_url == acquisition.ARTICLE_URL and timeout == 30
        self.calls += 1
        response = next(self.responses)
        if isinstance(response, Exception):
            raise response
        return response


@pytest.mark.parametrize(
    "url",
    [
        "http://link.springer.com" + acquisition.ALLOWED_PATH,
        "https://link.springer.com.evil.test" + acquisition.ALLOWED_PATH,
        "https://user:secret@link.springer.com" + acquisition.ALLOWED_PATH,
        "https://link.springer.com:8443" + acquisition.ALLOWED_PATH,
        "https://127.0.0.1/",
        "https://link.springer.com/another-article",
    ],
)
def test_redirect_destinations_are_fixed(url):
    with pytest.raises(acquisition.AcquisitionError, match="unapproved_redirect"):
        acquisition.ArticleRedirects().redirect_request(
            Request(acquisition.ARTICLE_URL), None, 302, "redirect", {}, url
        )


def test_download_types_size_and_bounded_retry(article, monkeypatch):
    body, _ = article
    headers = Message()
    headers["Retry-After"] = "3"
    failure = HTTPError(acquisition.ARTICLE_URL, 429, "limited", headers, None)
    opener = Opener(failure, Response(body))
    waits = []
    assert acquisition.download(opener=opener, sleep=waits.append)[0] == body
    assert waits == [3] and opener.calls == 2
    # Replace the first value, rather than append a second HTTP header.
    headers.replace_header("Retry-After", "999")
    with pytest.raises(acquisition.AcquisitionError, match="retry_deferred"):
        acquisition.download(opener=Opener(failure), sleep=waits.append)
    with pytest.raises(acquisition.AcquisitionError, match="content_type"):
        acquisition.download(opener=Opener(Response(body, "application/pdf")))
    monkeypatch.setattr(acquisition, "MAX_BYTES", 10)
    with pytest.raises(acquisition.AcquisitionError, match="artifact_size"):
        acquisition.download(opener=Opener(Response(body)))


def test_access_denial_is_not_retried_or_bypassed():
    opener = Opener(HTTPError(acquisition.ARTICLE_URL, 403, "denied", Message(), None))
    with pytest.raises(acquisition.AcquisitionError, match="http_failure"):
        acquisition.download(opener=opener)
    assert opener.calls == 1


@pytest.mark.parametrize(
    "change,reason",
    [
        (lambda b: b.replace(b"Attribution 4.0", b"Attribution NonCommercial 4.0"), "permission"),
        (lambda b: b.replace(b"Adults only.", b"All populations."), "extraction_change"),
        (lambda b: b.replace(b'id="Sec5"', b'id="Changed"'), "extraction_section"),
    ],
)
def test_rights_and_extraction_drift_quarantined(article, change, reason):
    body, recipe = article
    with pytest.raises(acquisition.AcquisitionError, match=reason):
        acquisition.extract(change(body), recipe)


def test_nc_recipe_cannot_approve_download(article):
    body, recipe = article
    recipe["source"]["license"] = "CC-BY-NC-4.0"
    with pytest.raises(acquisition.AcquisitionError, match="unapproved_license"):
        acquisition.extract(body, recipe)


def test_cache_resume_tampering_and_atomic_publish(article, monkeypatch, tmp_path):
    body, recipe = article
    monkeypatch.setattr(acquisition, "download", lambda: (body, acquisition.ARTICLE_URL))
    source, manifest = acquisition.acquire(tmp_path, recipe)
    monkeypatch.setattr(acquisition, "download", lambda: pytest.fail("resume must not fetch"))
    assert acquisition.acquire(tmp_path, recipe) == (source, manifest)
    catalog_path = tmp_path / "catalog.json"
    acquisition.write_json(catalog_path, {"version": 1, "sources": [catalog_source()]})
    acquisition.publish(source, catalog_path)
    acquisition.publish(source, catalog_path)
    assert len(json.loads(catalog_path.read_text())["sources"]) == 2
    before = catalog_path.read_bytes()
    source["chunks"][0]["content"] = "Unreviewed dosing"
    with pytest.raises(acquisition.AcquisitionError, match="manifest_mismatch"):
        acquisition.publish(source, catalog_path)
    assert catalog_path.read_bytes() == before
    (tmp_path / manifest["artifact_file"]).write_bytes(b"corrupted")
    with pytest.raises(acquisition.AcquisitionError, match="integrity_failure"):
        acquisition.acquire(tmp_path, recipe)


def test_failed_refresh_retains_previous_capture(article, monkeypatch, tmp_path):
    body, recipe = article
    monkeypatch.setattr(acquisition, "download", lambda: (body, acquisition.ARTICLE_URL))
    acquisition.acquire(tmp_path, recipe)
    before = (tmp_path / "s4-manifest.json").read_bytes()
    monkeypatch.setattr(acquisition, "download", lambda: (b"challenge", acquisition.ARTICLE_URL))
    with pytest.raises(acquisition.AcquisitionError):
        acquisition.acquire(tmp_path, recipe, refresh=True)
    assert (tmp_path / "s4-manifest.json").read_bytes() == before


def test_resume_rejects_manifest_path_traversal(article, monkeypatch, tmp_path):
    body, recipe = article
    monkeypatch.setattr(acquisition, "download", lambda: (body, acquisition.ARTICLE_URL))
    _, manifest = acquisition.acquire(tmp_path, recipe)
    manifest["artifact_file"] = "../private.html"
    acquisition.write_json(tmp_path / "s4-manifest.json", manifest)
    with pytest.raises(acquisition.AcquisitionError, match="artifact_path"):
        acquisition.acquire(tmp_path, recipe)


def test_provenance_failure_happens_before_embeddings_and_rolls_back(
    article, monkeypatch, tmp_path, session
):
    body, recipe = article
    monkeypatch.setattr(acquisition, "download", lambda: (body, acquisition.ARTICLE_URL))
    source, _ = acquisition.acquire(tmp_path, recipe)
    data = {"version": 1, "sources": [catalog_source(), source]}
    provider = FakeEmbeddings()
    seed_catalog(session, provider, data)
    session.commit()
    changed = copy.deepcopy(data)
    changed["sources"][1]["chunks"][0]["content"] = "Unreviewed"
    with pytest.raises(acquisition.AcquisitionError):
        seed_catalog(session, provider, changed)
    session.rollback()
    assert len(provider.calls) == 2
    stored = session.get(KnowledgeChunk, source["chunks"][0]["id"])
    assert stored.content == "Adults only.\n\nNot causal."
    changed["sources"][1]["review_status"] = "excluded"
    seed_catalog(session, provider, changed)
    assert len(session.scalars(select(KnowledgeChunk)).all()) == 1
