#!/usr/bin/env python3
"""Explicit maintenance backup, empty-target restore and privacy-safe health checks."""

import argparse
import hashlib
import json
import os
import ssl
import subprocess
import tarfile
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import urlopen

REPOSITORY = Path(__file__).resolve().parents[2]


def compose(args, *command, **kwargs):
    return subprocess.run(
        [
            "docker",
            "compose",
            "--env-file",
            str(Path(args.env_file).resolve()),
            "-f",
            str(REPOSITORY / "docker-compose.production.yml"),
            "-p",
            args.project,
            *command,
        ],
        check=True,
        **kwargs,
    )


def digest(path):
    with path.open("rb") as source:
        return hashlib.file_digest(source, "sha256").hexdigest()


def running(args):
    return compose(
        args, "ps", "--services", "--status", "running", capture_output=True, text=True
    ).stdout.splitlines()


def backup(args):
    if not args.maintenance:
        raise ValueError(
            "Backup requires --maintenance: writers are stopped briefly for consistency"
        )
    state = Path(args.state_dir).resolve()
    if not (state / "secrets").is_dir():
        raise ValueError("The configured deployment state directory is required")
    output = Path(args.directory).resolve()
    if output.exists():
        raise ValueError("Use a new private backup directory")
    os.umask(0o077)
    output.mkdir(parents=True, mode=0o700)
    active = running(args)
    writers = [
        name
        for name in [
            "gateway",
            "backend",
            "keycloak",
            "compreface-fe",
            "compreface-api",
            "compreface-admin",
            "compreface-core",
        ]
        if name in active
    ]
    databases = [
        ("postgres", "postgres", "academia", "academia_app"),
        ("postgres", "postgres", "keycloak", "academia_identity"),
    ]
    if "compreface-postgres-db" in active:
        databases.append(("compreface-postgres-db", "biometrics", "biometrics", "biometrics"))
    manifest = {
        "project": args.project,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "databases": [],
        "sha256": {},
    }
    try:
        if writers:
            compose(args, "stop", *writers, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        for service, user, database, owner in databases:
            filename = database + ".dump"
            with (output / filename).open("wb") as target:
                compose(
                    args,
                    "exec",
                    "-T",
                    service,
                    "pg_dump",
                    "-U",
                    user,
                    "-Fc",
                    "--no-owner",
                    "--no-acl",
                    database,
                    stdout=target,
                    stderr=subprocess.PIPE,
                )
            manifest["databases"].append(
                dict(service=service, user=user, database=database, owner=owner, file=filename)
            )
        with tarfile.open(output / "configuration.tar.gz", "w:gz") as archive:
            for name in ["secrets", "tls", "nginx.conf"]:
                archive.add(state / name, arcname="state/" + name, recursive=True)
            archive.add(args.env_file, arcname="env.production")
        for file in output.iterdir():
            manifest["sha256"][file.name] = digest(file)
        (output / "manifest.json").write_text(json.dumps(manifest, indent=2))
    finally:
        if writers:
            compose(args, "start", *writers, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    print("Backup completed. Store it on encrypted media and replicate it off-host.")


def verify_backup(directory):
    root = Path(directory).resolve()
    manifest = json.loads((root / "manifest.json").read_text())
    expected = {"academia.dump", "keycloak.dump", "configuration.tar.gz"}
    if not expected.issubset(manifest["sha256"]):
        raise ValueError("Incomplete backup")
    for name, checksum in manifest["sha256"].items():
        if Path(name).name != name or digest(root / name) != checksum:
            raise ValueError("Backup integrity check failed")
    allowed = {
        ("postgres", "postgres", "academia", "academia_app", "academia.dump"),
        ("postgres", "postgres", "keycloak", "academia_identity", "keycloak.dump"),
        ("compreface-postgres-db", "biometrics", "biometrics", "biometrics", "biometrics.dump"),
    }
    entries = {
        tuple(item[key] for key in ["service", "user", "database", "owner", "file"])
        for item in manifest["databases"]
    }
    if not entries <= allowed or not {row for row in allowed if row[0] == "postgres"} <= entries:
        raise ValueError("Unexpected database restoration target")
    if any(row[4] not in manifest["sha256"] for row in entries):
        raise ValueError("Unchecked database archive")
    return root, manifest


def restore(args):
    root, manifest = verify_backup(args.directory)
    if not args.empty_target or args.project == manifest["project"]:
        raise ValueError("Restore requires --empty-target and a different isolated project")
    active = running(args)
    if set(active) - {"postgres", "compreface-postgres-db"}:
        raise ValueError("Only target database containers may be running during restoration")
    # Validate ALL target databases before importing any data. Never clean a populated DB.
    for item in manifest["databases"]:
        count = compose(
            args,
            "exec",
            "-T",
            item["service"],
            "psql",
            "-U",
            item["user"],
            "-d",
            item["database"],
            "-Atc",
            "SELECT count(*) FROM pg_tables "
            "WHERE schemaname NOT IN ('pg_catalog','information_schema')",
            capture_output=True,
            text=True,
        ).stdout.strip()
        if count != "0":
            raise ValueError("Refusing to restore over a populated database")
    for item in manifest["databases"]:
        with (root / item["file"]).open("rb") as source:
            compose(
                args,
                "exec",
                "-T",
                item["service"],
                "pg_restore",
                "-U",
                item["user"],
                "--no-owner",
                "--no-acl",
                "--exit-on-error",
                "--role",
                item["owner"],
                "-d",
                item["database"],
                stdin=source,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
            )
    print(
        "Database restore completed in the isolated target. Verify matching secrets before startup."
    )


def health(args):
    result = compose(args, "ps", "--format", "json", capture_output=True, text=True).stdout.strip()
    rows = (
        json.loads(result)
        if result.startswith("[")
        else [json.loads(row) for row in result.splitlines()]
    )
    states = {
        row["Service"]: {"state": row["State"], "health": row.get("Health", "")} for row in rows
    }
    valid = all(
        states.get(service, {}).get("state") == "running"
        and states[service]["health"] in {"", "healthy"}
        for service in ["gateway", "backend", "postgres", "keycloak"]
    )
    if args.url:
        if not args.url.startswith("https://"):
            raise ValueError("Health verification requires HTTPS")
        context = ssl.create_default_context(cafile=args.ca_file)
        for path in ["/api/health", "/auth/realms/academia/.well-known/openid-configuration"]:
            with urlopen(args.url.rstrip("/") + path, timeout=10, context=context) as response:
                payload = json.loads(response.read(131072))
            valid = valid and (
                payload.get("status") == "ok"
                if path == "/api/health"
                else payload.get("issuer") == args.url.rstrip("/") + "/auth/realms/academia"
            )
    print(json.dumps({"healthy": valid, "services": states}))
    return 0 if valid else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env-file", default=".env.production")
    parser.add_argument("--project", default="academia-production")
    commands = parser.add_subparsers(dest="command", required=True)
    command = commands.add_parser("backup")
    command.add_argument("--state-dir", default=".deployment")
    command.add_argument("--directory", required=True)
    command.add_argument("--maintenance", action="store_true")
    command = commands.add_parser("restore")
    command.add_argument("--directory", required=True)
    command.add_argument("--empty-target", action="store_true")
    command = commands.add_parser("health")
    command.add_argument("--url")
    command.add_argument("--ca-file")
    args = parser.parse_args()
    try:
        result = {"backup": backup, "restore": restore, "health": health}[args.command](args)
        raise SystemExit(result or 0)
    except (ValueError, KeyError, OSError, subprocess.CalledProcessError, tarfile.TarError):
        parser.exit(
            1,
            "Operation failed. Check configuration, service status "
            "and the documented prerequisites.\n",
        )


if __name__ == "__main__":
    main()
