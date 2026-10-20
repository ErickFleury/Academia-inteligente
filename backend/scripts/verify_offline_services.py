"""Protocol checks for the isolated, provisioned offline Compose test stack.

Reads only the public .env.example fixture; never use against a real deployment.
The internal Docker network deliberately blocks outbound internet. Browser
rendering is covered separately by frontend tests, not claimed by this probe.
"""

import base64
import hashlib
import json
import os
import smtplib
import socket
import sys
from email.message import EmailMessage
from html.parser import HTMLParser
from http.cookiejar import CookieJar
from pathlib import Path
from types import SimpleNamespace
from urllib.error import HTTPError
from urllib.parse import parse_qs, urlencode, urlsplit
from urllib.request import (
    HTTPCookieProcessor,
    HTTPRedirectHandler,
    ProxyHandler,
    Request,
    build_opener,
)
from uuid import uuid4


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, request, response, code, message, headers, url):
        return None


class LocalHttp:
    def __init__(self):
        self.opener = build_opener(ProxyHandler({}), HTTPCookieProcessor(CookieJar()), NoRedirect())

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def get(self, url, *, params=None, headers=None):
        if params:
            url += "?" + urlencode(params)
        return self.request(Request(url, headers=headers or {}))

    def post(self, url, *, data):
        return self.request(Request(url, data=urlencode(data).encode(), method="POST"))

    def request(self, request):
        try:
            response = self.opener.open(request, timeout=10)
        except HTTPError as error:
            response = error
        with response:
            body = response.read().decode()
            return SimpleNamespace(
                status_code=response.code,
                text=body,
                headers=response.headers,
                json=lambda: json.loads(body),
            )


class LoginForm(HTMLParser):
    action = None

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        if tag == "form" and values.get("id") == "kc-form-login":
            self.action = values["action"]


def run():
    assert os.environ["AI_PROVIDER"] == os.environ["AI_EMBEDDING_PROVIDER"] == "ollama"
    assert not os.getenv("OPENAI_API_KEY")
    fixture = Path(sys.argv[1])
    assert fixture.name == ".env.example"
    values = dict(
        line.split("=", 1)
        for line in fixture.read_text().splitlines()
        if "=" in line and not line.lstrip().startswith("#")
    )
    with socket.socket() as probe:
        probe.settimeout(2)
        try:
            probe.connect(("1.1.1.1", 443))
        except OSError:
            pass
        else:
            raise AssertionError("External network is reachable")
    print("PASS local providers, no paid key, outbound internet blocked", flush=True)
    with LocalHttp() as http:
        assert http.get("http://backend:8000/health").status_code == 200
        assert (
            http.get("http://frontend:5173", headers={"Host": "localhost:5173"}).status_code == 200
        )
        verifier = uuid4().hex + uuid4().hex
        challenge = (
            base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest())
            .rstrip(b"=")
            .decode()
        )
        redirect = "http://localhost:5173/"
        login = http.get(
            "http://keycloak:8080/realms/academia/protocol/openid-connect/auth",
            params={
                "client_id": "academia-web",
                "redirect_uri": redirect,
                "response_type": "code",
                "scope": "openid",
                "code_challenge": challenge,
                "code_challenge_method": "S256",
            },
        )
        assert login.status_code == 200
        form = LoginForm()
        form.feed(login.text)
        assert form.action
        action = urlsplit(form.action)
        logged_in = http.post(
            "http://keycloak:8080" + action.path + "?" + action.query,
            data={
                "username": values["APP_ADMIN_USERNAME"],
                "password": values["APP_ADMIN_PASSWORD"],
            },
        )
        assert logged_in.status_code == 302, "Local login did not complete"
        code = parse_qs(urlsplit(logged_in.headers["location"]).query)["code"][0]
        exchanged = http.post(
            "http://keycloak:8080/realms/academia/protocol/openid-connect/token",
            data={
                "client_id": "academia-web",
                "grant_type": "authorization_code",
                "redirect_uri": redirect,
                "code": code,
                "code_verifier": verifier,
            },
        )
        assert exchanged.status_code == 200
        token = exchanged.json()["access_token"]
        response = http.get(
            "http://backend:8000/ai/references", headers={"Authorization": "Bearer " + token}
        )
        assert response.status_code == 200, "Authenticated local API request failed"
        print(
            "PASS frontend delivery, local Keycloak PKCE login and authenticated admin API",
            flush=True,
        )
        subject = "Synthetic offline mailbox check " + uuid4().hex
        message = EmailMessage()
        message["From"] = "no-reply@academia.local"
        message["To"] = "offline-fixture@example.test"
        message["Subject"] = subject
        message.set_content("Synthetic local-only verification. No client information.")
        with smtplib.SMTP("mailpit", 1025, timeout=5) as smtp:
            smtp.send_message(message)
        mailbox = http.get("http://mailpit:8025/api/v1/messages").json()
        assert any(row["Subject"] == subject for row in mailbox["messages"])
        print("PASS local SMTP delivery and mailbox retrieval", flush=True)
    print(json.dumps({"offline_protocol_checks": "passed", "browser_rendering": "not_exercised"}))


if __name__ == "__main__":
    run()
