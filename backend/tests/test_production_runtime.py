from unittest.mock import MagicMock

import pytest

from app.integrations.email import SmtpEmailSender
from app.runtime import load_secret_files


def test_secret_file_is_loaded_without_modifying_the_source_environment(tmp_path):
    secret = tmp_path / "secret"
    secret.write_text("private-value\n")
    original = {"SMTP_PASSWORD_FILE": str(secret), "PATH": "/usr/bin"}
    result = load_secret_files(original)
    assert result == {"SMTP_PASSWORD": "private-value", "PATH": "/usr/bin"}
    assert "SMTP_PASSWORD_FILE" in original


@pytest.mark.parametrize("data", [b"", b"\xff", b"secret\x00", b"x" * 65_537])
def test_invalid_secret_file_fails_without_exposing_content(tmp_path, data):
    secret = tmp_path / "secret"
    secret.write_bytes(data)
    with pytest.raises(ValueError, match="^Unable to load SMTP_PASSWORD_FILE$"):
        load_secret_files({"SMTP_PASSWORD_FILE": str(secret)})


def test_missing_and_ambiguous_secrets_fail_closed(tmp_path):
    with pytest.raises(ValueError, match="Unable to load DATABASE_URL_FILE"):
        load_secret_files({"DATABASE_URL_FILE": str(tmp_path / "missing")})
    with pytest.raises(ValueError, match="Configure either DATABASE_URL"):
        load_secret_files({"DATABASE_URL_FILE": "file", "DATABASE_URL": "private-value"})


def test_unapproved_file_variables_cannot_replace_runtime_commands(tmp_path):
    assert load_secret_files({"PATH_FILE": str(tmp_path)}) == {"PATH_FILE": str(tmp_path)}


@pytest.fixture
def smtp_environment(monkeypatch):
    for key in ["SMTP_SECURITY", "SMTP_USERNAME", "SMTP_PASSWORD"]:
        monkeypatch.delenv(key, raising=False)
    return monkeypatch


@pytest.mark.parametrize("security", ["none", "starttls", "tls"])
def test_email_preserves_delivery_and_negotiates_verified_tls_when_requested(
    smtp_environment, security
):
    smtp_environment.setenv("SMTP_SECURITY", security)
    plain, encrypted = MagicMock(), MagicMock()
    smtp_environment.setattr("app.integrations.email.smtplib.SMTP", plain)
    smtp_environment.setattr("app.integrations.email.smtplib.SMTP_SSL", encrypted)
    if security != "none":
        smtp_environment.setenv("SMTP_USERNAME", "relay-user")
        smtp_environment.setenv("SMTP_PASSWORD", "test-only-secret")
    SmtpEmailSender("relay", 587, "gym@example.test").send(
        recipient="client@example.test", subject="Convite", body="Seu convite."
    )
    selected = encrypted if security == "tls" else plain
    other = plain if security == "tls" else encrypted
    other.assert_not_called()
    smtp = selected.return_value.__enter__.return_value
    if security == "starttls":
        smtp.starttls.assert_called_once()
        assert smtp.starttls.call_args.kwargs["context"].check_hostname
    if security == "tls":
        assert selected.call_args.kwargs["context"].check_hostname
    if security != "none":
        smtp.login.assert_called_once_with("relay-user", "test-only-secret")
    else:
        smtp.login.assert_not_called()
    message = smtp.send_message.call_args.args[0]
    assert message["To"] == "client@example.test"
    assert message["Subject"] == "Convite"


def test_plaintext_smtp_cannot_send_credentials(smtp_environment):
    smtp_environment.setenv("SMTP_USERNAME", "relay-user")
    smtp_environment.setenv("SMTP_PASSWORD", "test-only-secret")
    with pytest.raises(ValueError, match="SMTP authentication requires TLS"):
        SmtpEmailSender()


def test_failed_tls_negotiation_never_falls_back_to_plaintext_delivery(smtp_environment):
    smtp_environment.setenv("SMTP_SECURITY", "starttls")
    connection = MagicMock()
    smtp_environment.setattr("app.integrations.email.smtplib.SMTP", connection)
    smtp = connection.return_value.__enter__.return_value
    smtp.starttls.side_effect = OSError("TLS unavailable")
    with pytest.raises(OSError, match="TLS unavailable"):
        SmtpEmailSender("relay", 587).send(
            recipient="client@example.test", subject="Convite", body="Seu convite."
        )
    smtp.send_message.assert_not_called()
    smtp.login.assert_not_called()
