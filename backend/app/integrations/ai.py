from typing import Protocol


class TrainingGenerationProvider(Protocol):
    def generate(self, *, prompt: str) -> str: ...
