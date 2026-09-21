"""E-mail integration boundary for provider-specific delivery."""

import os
import smtplib
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

    def send(self, *, recipient: str, subject: str, body: str) -> None:
        if not self._host:
            raise OSError("SMTP host is not configured")
        message = EmailMessage()
        message["From"] = self._sender
        message["To"] = recipient
        message["Subject"] = subject
        message.set_content(body)
        with smtplib.SMTP(self._host, self._port, timeout=5) as smtp:
            smtp.send_message(message)
