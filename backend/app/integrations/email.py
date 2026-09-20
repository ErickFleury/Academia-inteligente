from typing import Protocol


class EmailSender(Protocol):
    def send(self, *, recipient: str, subject: str, body: str) -> None: ...
