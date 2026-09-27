"""E-mail integration boundary for provider-specific delivery."""

import os
import smtplib
import ssl
from email.message import EmailMessage
from typing import Protocol


class EmailSender(Protocol):
    def send(self, *, recipient: str, subject: str, body: str) -> None: ...


class SmtpEmailSender:
    """Deliver plain-text messages through the configured SMTP relay."""

    def __init__(
        self,
        host: str | None = None,
        port: int | None = None,
        sender: str | None = None,
    ) -> None:
        self._host = host or os.environ.get("SMTP_HOST", "")
        self._port = port or int(os.environ.get("SMTP_PORT", "1025"))
        self._sender = sender or os.environ.get("SMTP_FROM", "no-reply@academia.local")
        self._security = os.environ.get("SMTP_SECURITY", "none")
        self._username = os.environ.get("SMTP_USERNAME", "")
        self._password = os.environ.get("SMTP_PASSWORD", "")
        if self._security not in {"none", "starttls", "tls"}:
            raise ValueError("SMTP_SECURITY must be none, starttls or tls")
        if bool(self._username) != bool(self._password):
            raise ValueError("SMTP authentication requires both username and password")
        if self._username and self._security == "none":
            raise ValueError("SMTP authentication requires TLS")

    def send(self, *, recipient: str, subject: str, body: str) -> None:
        if not self._host:
            raise OSError("SMTP host is not configured")
        message = EmailMessage()
        message["From"] = self._sender
        message["To"] = recipient
        message["Subject"] = subject
        message.set_content(body)
        factory = smtplib.SMTP_SSL if self._security == "tls" else smtplib.SMTP
        options = {"context": ssl.create_default_context()} if self._security == "tls" else {}
        with factory(self._host, self._port, timeout=5, **options) as smtp:
            if self._security == "starttls":
                smtp.starttls(context=ssl.create_default_context())
            if self._username:
                smtp.login(self._username, self._password)
            smtp.send_message(message)
