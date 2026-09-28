import importlib.util
import json
import os
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[2]


def module(name):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).with_name(name + ".py"))
    loaded = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loaded)
    return loaded


prepare = module("prepare")


def settings(tmp_path):
    secret = tmp_path / "smtp-source"
    secret.write_text("synthetic-secret")
    return SimpleNamespace(
        domain="gym.example.test",
        admin_network="203.0.113.4/32",
        state_dir=str(tmp_path / "state"),
        env_file=str(tmp_path / "env"),
        smtp_host="smtp.example.test",
        smtp_port=587,
        smtp_security="starttls",
        smtp_from="gym@example.test",
        smtp_username="relay",
        smtp_password_file=str(secret),
        openai_key_file=None,
        compreface_key_file=None,
        admin_username="admin",
    )


def test_preparation_keeps_secrets_private_and_does_not_force_mfa(tmp_path):
    args = settings(tmp_path)
    old = os.umask(0o077)
    try:
        prepare.prepare(args)
    finally:
        os.umask(old)
    state = Path(args.state_dir)
    realm = json.loads((state / "secrets/academia-realm.json").read_text())
    assert realm["bruteForceProtected"] and not realm["permanentLockout"]
    assert realm["ssoSessionIdleTimeout"] == 300
    assert realm["resetPasswordAllowed"] is True
    assert realm["attributes"]["actionTokenGeneratedByUserLifespan.reset-credentials"] == "900"
    assert not any(action.get("defaultAction") for action in realm["requiredActions"])
    otp = next(action for action in realm["requiredActions"] if action["alias"] == "CONFIGURE_TOTP")
    assert otp["enabled"]
    assert all("CONFIGURE_TOTP" not in user.get("requiredActions", []) for user in realm["users"])
    web = next(client for client in realm["clients"] if client["clientId"] == "academia-web")
    assert web["redirectUris"] == ["https://gym.example.test/"]
    assert web["attributes"]["pkce.code.challenge.method"] == "S256"
    assert realm["smtpServer"]["starttls"] == "true"
    assert realm["smtpServer"]["password"] == "synthetic-secret"
    assert "synthetic-secret" not in Path(args.env_file).read_text()
    assert state.stat().st_mode & 0o077 == 0
    assert Path(args.env_file).stat().st_mode & 0o077 == 0
    original = (state / "secrets/app_admin_password").read_text()
    with pytest.raises(ValueError, match="Refusing to overwrite"):
        prepare.prepare(args)
    assert (state / "secrets/app_admin_password").read_text() == original


@pytest.mark.parametrize(
    "domain",
    [
        "evil;include.conf",
        "https://example.com",
        "example.com/abc",
        "example.com\n",
        "-bad.example",
        "example.com:443",
    ],
)
def test_domain_cannot_inject_proxy_configuration(domain):
    with pytest.raises(ValueError):
        prepare.domain_name(domain)


def test_operator_network_cannot_open_identity_administration_to_everyone(tmp_path):
    args = settings(tmp_path)
    args.admin_network = "0.0.0.0/0"
    with pytest.raises(ValueError):
        prepare.prepare(args)
    assert not Path(args.state_dir).exists()


def test_optional_provider_definition_snapshot_preserves_local_behavior():
    original = (ROOT / "docker-compose.yml").read_text()
    unchanged = original[original.index("  ollama:") : original.index("\nnetworks:")]
    assert unchanged in (ROOT / "docs/deployment/providers.yml").read_text()
