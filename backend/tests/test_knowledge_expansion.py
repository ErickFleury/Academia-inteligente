"""Offline safeguards for the licensed expansion, not scientific efficacy tests."""

import copy
import json
from email.message import Message
from io import BytesIO
from urllib.request import Request

import pytest

from app.modules.knowledge import acquisition_expansion as expansion
from app.modules.knowledge.acquisition import AcquisitionError, digest, validate_packaged_source


@pytest.fixture
def article():
    recipe = json.loads(expansion.RECIPE_PATH.read_text(encoding="utf-8"))
    entry = copy.deepcopy(recipe["entries"][0])
    entry["source"]["title"] = "Offline fixture"
    entry["source"]["authors"] = ["Fixture Author"]
    entry["selections"] = [
        {
            "id": entry["source"]["id"] + "-fixture",
            "selectors": [{"tag": "sec", "id": "dose"}, {"tag": "sec", "id": "limits"}],
            "locator": "Fixture dose and limitations",
            "text_sha256": digest(b"Dose\n\nFixture dose.\n\nLimits\n\nAdults only."),
        }
    ]
    body = f"""<article><front><article-meta>
      <article-id pub-id-type="pmcid">{entry["pmc"]}</article-id>
      <article-id pub-id-type="doi">{entry["doi"]}</article-id>
      <title-group><article-title>Offline fixture</article-title></title-group>
      <contrib-group content-type="author"><contrib><name><given-names>Fixture</given-names>
      <surname>Author</surname></name></contrib></contrib-group>
      <permissions><license><license-p>CC BY
      <ext-link href="https://creativecommons.org/licenses/by/4.0/">License</ext-link>
      </license-p></license></permissions></article-meta></front><body>
      <sec id="dose"><title>Dose</title><p>Fixture dose.</p>
      <fig><caption>EXCLUDED MEDIA</caption></fig></sec>
      <sec id="limits"><title>Limits</title><p>Adults only.</p></sec>
      </body></article>""".encode()
    return body, entry


def test_extract_keeps_scope_and_excludes_media(article):
    body, entry = article
    chunks, rights = expansion.extract(body, entry)
    assert "Adults only." in chunks[0]["content"]
    assert "EXCLUDED MEDIA" not in chunks[0]["content"]
    assert "licenses/by/4.0" in rights


@pytest.mark.parametrize(
    "old,new,reason",
    [
        (b"licenses/by/4.0", b"licenses/by-nc/4.0", "permission"),
        (b"Fixture dose.", b"Changed dose.", "extraction_change"),
        (b"Offline fixture", b"Different article", "identity"),
        (b'id="limits"', b'id="missing"', "extraction_section"),
    ],
)
def test_permission_identity_scope_and_drift_fail_closed(article, old, new, reason):
    body, entry = article
    with pytest.raises(AcquisitionError, match=reason):
        expansion.extract(body.replace(old, new), entry)


def test_ambiguous_sections_and_xml_entities_reject(article):
    body, entry = article
    duplicate = b'<sec id="limits"><title>Other limits</title><p>Other.</p></sec>'
    with pytest.raises(AcquisitionError, match="ambiguous"):
        expansion.extract(body.replace(b"</body>", duplicate + b"</body>"), entry)
    with pytest.raises(AcquisitionError, match="invalid_xml"):
        expansion.extract(b'<!ENTITY x "entity">' + body, entry)


def test_table_preserves_headers_spans_units_and_footnotes():
    from xml.etree import ElementTree as ET

    table = ET.fromstring("""<table-wrap><label>Table 1</label><caption><p>Fixture</p></caption>
      <table><thead><tr><th rowspan="2">Dose</th><th>Time (seconds)</th></tr></thead>
      <tbody><tr><td>Hold</td><td>10</td></tr></tbody></table>
      <table-wrap-foot><p>Conditional on screening.</p></table-wrap-foot></table-wrap>""")
    rendered = expansion.table_text(table)
    assert "[rowspan=2] Dose | Time (seconds)" in rendered
    assert "Hold | 10" in rendered
    assert "Conditional on screening." in rendered


def test_cached_bytes_resume_and_corruption_does_not_replace_manifest(article, tmp_path):
    body, entry = article
    source, manifest = expansion.acquire(entry, tmp_path, fetch=lambda _: body)
    again, _ = expansion.acquire(
        entry, tmp_path, fetch=lambda _: pytest.fail("unchanged acquisition used network")
    )
    assert source == again
    path = tmp_path / (entry["source"]["id"] + "-manifest.json")
    previous = path.read_bytes()
    (tmp_path / manifest["artifact_file"]).write_bytes(b"corrupt")
    with pytest.raises(AcquisitionError, match="integrity"):
        expansion.acquire(entry, tmp_path)
    assert path.read_bytes() == previous


def test_cached_path_and_unlisted_article_cannot_select_files_or_network(article, tmp_path):
    body, entry = article
    _, manifest = expansion.acquire(entry, tmp_path, fetch=lambda _: body)
    manifest["artifact_sha256"] = "../outside"
    path = tmp_path / (entry["source"]["id"] + "-manifest.json")
    path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(AcquisitionError, match="path"):
        expansion.acquire(entry, tmp_path)
    with pytest.raises(AcquisitionError, match="unapproved_article"):
        expansion.article_url("https://127.0.0.1/")


def test_atomic_catalog_publish_and_provenance_cannot_be_stripped(article, tmp_path):
    body, entry = article
    source, _ = expansion.acquire(entry, tmp_path, fetch=lambda _: body)
    catalog = tmp_path / "catalog.json"
    original = {"version": 1, "sources": [{"id": "legacy", "unchanged": True}]}
    catalog.write_text(json.dumps(original), encoding="utf-8")
    bad = copy.deepcopy(source)
    bad["chunks"][0]["content"] = "Tampered"
    previous = catalog.read_bytes()
    with pytest.raises(AcquisitionError):
        expansion.publish_batch([source, bad], catalog)
    assert catalog.read_bytes() == previous
    stripped = copy.deepcopy(source)
    stripped.pop("provenance")
    with pytest.raises(AcquisitionError, match="missing_artifact"):
        validate_packaged_source(stripped)
    expansion.publish_batch([source], catalog)
    assert json.loads(catalog.read_text())["sources"][0] == original["sources"][0]


def test_redirect_denied_without_visiting_destination():
    with pytest.raises(AcquisitionError, match="redirect"):
        expansion.NoRedirects().redirect_request(
            Request(expansion.article_url("PMC11349676")),
            None,
            302,
            "redirect",
            {},
            "http://127.0.0.1/",
        )


def test_download_content_type_and_size_are_bounded(article, monkeypatch):
    body, entry = article

    class Response(BytesIO):
        url = expansion.article_url(entry["pmc"])

        def __init__(self, media_type):
            super().__init__(body)
            self.headers = Message()
            self.headers["Content-Type"] = media_type

    class Opener:
        def __init__(self, media_type):
            self.media_type = media_type

        def open(self, request, *, timeout):
            assert timeout == 30
            return Response(self.media_type)

    assert expansion.download(entry["pmc"], opener=Opener("application/xml")) == body
    with pytest.raises(AcquisitionError, match="content_type"):
        expansion.download(entry["pmc"], opener=Opener("text/html"))
    monkeypatch.setattr(expansion, "MAX_BYTES", 10)
    with pytest.raises(AcquisitionError, match="artifact_size"):
        expansion.download(entry["pmc"], opener=Opener("application/xml"))


def test_packaged_expansion_matches_reviewed_selection_pins():
    recipe = json.loads(expansion.RECIPE_PATH.read_text(encoding="utf-8"))
    catalog = json.loads(expansion.CATALOG_PATH.read_text(encoding="utf-8"))
    sources = {s["id"]: s for s in catalog["sources"]}
    assert len(recipe["entries"]) == len(expansion.ARTICLES) == 9
    for entry in recipe["entries"]:
        source = sources[entry["source"]["id"]]
        validate_packaged_source(source)
        assert source["provenance"]["scientific_approval"] == "pending"
        assert source["provenance"]["recipe_sha256"] == digest(
            json.dumps(entry, sort_keys=True).encode()
        )
        assert [(c["id"], digest(c["content"].encode())) for c in source["chunks"]] == [
            (c["id"], c["text_sha256"]) for c in entry["selections"]
        ]
