#!/usr/bin/env python3
"""Prepare a NEW production deployment without touching Docker, DNS or host rules."""

import argparse
import ipaddress
import json
import os
import re
import secrets
from pathlib import Path

REPOSITORY = Path(__file__).resolve().parents[2]


def domain_name(value: str) -> str:
    value = value.lower()
    if (
        len(value) > 253
        or "." not in value
        or not all(
            re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?", label)
            for label in value.split(".")
        )
    ):
        raise ValueError("Use a DNS hostname without a scheme, port or path")
    return value


def build_realm(domain: str, smtp: dict, values: dict) -> dict:
    realm = json.loads(
        (REPOSITORY / "backend/app/modules/identity/keycloak/realm-academia.json").read_text()
    )
    realm.update(
        bruteForceProtected=True,
        permanentLockout=False,
        failureFactor=10,
        waitIncrementSeconds=30,
        minimumQuickLoginWaitSeconds=30,
        maxFailureWaitSeconds=900,
        maxDeltaTimeSeconds=43200,
        sslRequired="external",
        eventsEnabled=True,
        eventsExpiration=604800,
        eventsListeners=[],
        adminEventsEnabled=True,
        adminEventsDetailsEnabled=False,
    )
    realm["smtpServer"] = smtp
    # Make enrollment available for a future operator decision without assigning it.
    realm["requiredActions"].append(
        dict(
            alias="CONFIGURE_TOTP",
            name="Configure OTP",
            providerId="CONFIGURE_TOTP",
            enabled=True,
            defaultAction=False,
            priority=10,
        )
    )
    for client in realm["clients"]:
        if client["clientId"] == "academia-web":
            client["redirectUris"] = [f"https://{domain}/"]
            client["webOrigins"] = [f"https://{domain}"]
            client["attributes"].update(
                {
                    "post.logout.redirect.uris": f"https://{domain}/",
                    "pkce.code.challenge.method": "S256",
                }
            )
        elif client["clientId"] == "academia-provisioner":
            client["secret"] = values["provisioning_secret"]
    for user in realm["users"]:
        if user["username"] == "${APP_ADMIN_USERNAME}":
            user["username"] = values["app_admin_username"]
            user["credentials"][0]["value"] = values["app_admin_password"]
    return realm


def read_secret(path: str | None) -> str:
    if path is None:
        return "not-configured"
    value = Path(path).read_text().rstrip("\r\n")
    if not value or "\x00" in value or len(value) > 65536:
        raise ValueError("Invalid supplied secret file")
    return value


def prepare(args) -> None:
    domain = domain_name(args.domain)
    management = ipaddress.ip_network(args.admin_network, strict=True)
    if management.prefixlen == 0:
        raise ValueError("Identity administration cannot be open to the whole Internet")
    state = Path(args.state_dir).resolve()
    env_file = Path(args.env_file).resolve()
    if state.exists() or env_file.exists():
        raise ValueError("Refusing to overwrite deployment state or rotate existing credentials")
    for value in [
        str(state),
        args.smtp_host,
        args.smtp_from,
        args.smtp_username,
        args.admin_username,
    ]:
        if not value or any(char in value for char in "\r\n\x00'\"$\\"):
            raise ValueError("Invalid deployment setting")
    if not 1 <= args.smtp_port <= 65535:
        raise ValueError("Invalid SMTP port")
    values = {
        name: secrets.token_hex(32)
        for name in [
            "postgres_password",
            "app_db_password",
            "keycloak_db_password",
            "keycloak_admin_password",
            "app_admin_password",
            "provisioning_secret",
            "access_secret",
        ]
    }
    values["app_admin_username"] = args.admin_username
    values["database_url"] = (
        f"postgresql+psycopg://academia_app:{values['app_db_password']}@postgres:5432/academia"
    )
    values["smtp_password"] = read_secret(args.smtp_password_file)
    values["openai_key"] = read_secret(args.openai_key_file)
    values["compreface_key"] = read_secret(args.compreface_key_file)
    smtp = dict(
        host=args.smtp_host,
        port=str(args.smtp_port),
        **{"from": args.smtp_from},
        auth="true",
        user=args.smtp_username,
        password=values["smtp_password"],
        ssl=str(args.smtp_security == "tls").lower(),
        starttls=str(args.smtp_security == "starttls").lower(),
    )
    realm = build_realm(domain, smtp, values)
    nginx = (REPOSITORY / "frontend/production/nginx.conf.template").read_text()
    nginx = nginx.replace("__DOMAIN__", domain).replace("__ADMIN_NETWORK__", str(management))
    os.umask(0o077)
    state.mkdir(parents=True, mode=0o700)
    (state / "secrets").mkdir(mode=0o700)
    # Only these directories are bind-mounted; the outer state directory stays private.
    for name in ["tls", "acme"]:
        (state / name).mkdir(mode=0o755)
        (state / name).chmod(0o755)
    for name, value in values.items():
        path = state / "secrets" / name
        path.write_text(value + "\n")
        # Compose binds each file individually. Host users cannot traverse the private parent.
        path.chmod(0o444)
    (state / "secrets/academia-realm.json").write_text(json.dumps(realm, indent=2))
    (state / "secrets/academia-realm.json").chmod(0o444)
    (state / "nginx.conf").write_text(nginx)
    (state / "nginx.conf").chmod(0o444)
    env_file.write_text(
        "\n".join(
            [
                f"APP_DOMAIN={domain}",
                f"PRODUCTION_STATE_DIR='{state}'",
                f"SMTP_HOST={args.smtp_host}",
                f"SMTP_PORT={args.smtp_port}",
                f"SMTP_SECURITY={args.smtp_security}",
                f"SMTP_USERNAME={args.smtp_username}",
                f"SMTP_FROM={args.smtp_from}",
                "AI_PROVIDER=openai",
                "FACIAL_ACCESS_MODE=disabled",
                "# Only used by the unchanged optional local biometric profile:",
                "COMPREFACE_DATABASE_PASSWORD=" + secrets.token_hex(32),
                "",
            ]
        )
    )
    env_file.chmod(0o600)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--domain", required=True)
    parser.add_argument("--admin-network", required=True, help="Trusted operator public IP/CIDR")
    parser.add_argument("--state-dir", default=".deployment")
    parser.add_argument("--env-file", default=".env.production")
    parser.add_argument("--admin-username", default="admin")
    parser.add_argument("--smtp-host", required=True)
    parser.add_argument("--smtp-port", type=int, default=587)
    parser.add_argument("--smtp-security", choices=["starttls", "tls"], default="starttls")
    parser.add_argument("--smtp-from", required=True)
    parser.add_argument("--smtp-username", required=True)
    parser.add_argument("--smtp-password-file", required=True)
    parser.add_argument("--openai-key-file")
    parser.add_argument("--compreface-key-file")
    args = parser.parse_args()
    try:
        prepare(args)
    except (ValueError, OSError):
        # Neither source file contents nor credentials belong in stdout/stderr.
        parser.exit(1, "Preparation failed: check inputs, permissions and existing output paths.\n")
    print("Prepared new deployment files. No services started or host rules changed.")


if __name__ == "__main__":
    main()
