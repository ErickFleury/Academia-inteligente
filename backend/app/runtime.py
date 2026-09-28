"""Load explicitly supported mounted secrets before starting a production process."""

import os
import sys
from pathlib import Path

SECRET_VARIABLES = (
    "DATABASE_URL",
    "KEYCLOAK_PROVISIONING_CLIENT_SECRET",
    "SMTP_PASSWORD",
    "OPENAI_API_KEY",
    "COMPREFACE_API_KEY",
    "ACCESS_EVENT_INTEGRATION_SECRET",
)


def load_secret_files(environment: dict[str, str]) -> dict[str, str]:
    """Fail closed on ambiguous configuration without including secret values."""
    result = environment.copy()
    for name in SECRET_VARIABLES:
        filename = result.pop(f"{name}_FILE", None)
        if filename is None:
            continue
        if result.get(name):
            raise ValueError(f"Configure either {name} or {name}_FILE, not both")
        try:
            with Path(filename).open("rb") as source:
                data = source.read(65_537)
            value = data.decode("utf-8").rstrip("\r\n")
            if not value or len(data) > 65_536 or "\x00" in value:
                raise ValueError
        except (OSError, UnicodeError, ValueError):
            raise ValueError(f"Unable to load {name}_FILE") from None
        result[name] = value
    return result


def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit("A runtime command is required")
    try:
        environment = load_secret_files(dict(os.environ))
    except ValueError as error:
        raise SystemExit(str(error)) from None
    os.execvpe(sys.argv[1], sys.argv[1:], environment)


if __name__ == "__main__":
    main()
