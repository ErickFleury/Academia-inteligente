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


operations = module("operations")
firewall = module("firewall-plan")


def test_firewall_plan_covers_ipv4_and_ipv6_without_executing_rules():
    plan = firewall.render("eth0", "203.0.113.4/32", 22)
    assert "iptables -I DOCKER-USER" in plan
    assert "ip6tables -I DOCKER-USER" in plan
    assert "--ctorigdstport 443" in plan
    for interface, network in [("eth0;id", "203.0.113.4/32"), ("eth0", "::/0")]:
        with pytest.raises(ValueError):
            firewall.render(interface, network, 22)


def test_backup_manifest_rejects_tampering_and_external_filenames(tmp_path):
    names = ["academia.dump", "keycloak.dump", "configuration.tar.gz"]
    for name in names:
        (tmp_path / name).write_bytes(b"synthetic-backup")
    manifest = {
        "project": "source",
        "databases": [
            dict(
                service="postgres", user="postgres", database=name, owner=owner, file=name + ".dump"
            )
            for name, owner in [("academia", "academia_app"), ("keycloak", "academia_identity")]
        ],
    }
    manifest["sha256"] = {name: operations.digest(tmp_path / name) for name in names}
    (tmp_path / "manifest.json").write_text(json.dumps(manifest))
    assert operations.verify_backup(tmp_path)[1]["project"] == "source"
    (tmp_path / "academia.dump").write_bytes(b"tampered")
    with pytest.raises(ValueError):
        operations.verify_backup(tmp_path)
    manifest["sha256"]["../outside.dump"] = "fake"
    (tmp_path / "manifest.json").write_text(json.dumps(manifest))
    with pytest.raises(ValueError):
        operations.verify_backup(tmp_path)


def test_failed_backup_restarts_only_originally_running_writers(tmp_path, monkeypatch):
    state = tmp_path / "state"
    (state / "secrets").mkdir(parents=True)
    args = SimpleNamespace(
        maintenance=True,
        state_dir=str(state),
        directory=str(tmp_path / "backup"),
        project="synthetic-source",
    )
    monkeypatch.setattr(operations, "running", lambda _: ["backend", "postgres"])
    commands = []

    def compose(_, *command, **kwargs):
        commands.append(command)
        if command[0] == "exec":
            raise OSError("Synthetic dump failure")

    monkeypatch.setattr(operations, "compose", compose)
    old = os.umask(0o077)
    try:
        with pytest.raises(OSError):
            operations.backup(args)
    finally:
        os.umask(old)
    assert commands[0] == ("stop", "backend")
    assert commands[-1] == ("start", "backend")
    assert not (tmp_path / "backup/manifest.json").exists()


def test_restore_checks_every_database_before_importing_any(tmp_path, monkeypatch):
    entries = [
        dict(service="postgres", user="postgres", database=name)
        for name in ["academia", "keycloak"]
    ]
    monkeypatch.setattr(
        operations,
        "verify_backup",
        lambda _: (tmp_path, {"project": "source", "databases": entries}),
    )
    monkeypatch.setattr(operations, "running", lambda _: ["postgres"])
    calls = []

    def compose(_, *command, **kwargs):
        calls.append(command)
        assert "pg_restore" not in command
        return SimpleNamespace(stdout="0" if len(calls) == 1 else "1")

    monkeypatch.setattr(operations, "compose", compose)
    with pytest.raises(ValueError, match="populated"):
        operations.restore(
            SimpleNamespace(directory=str(tmp_path), empty_target=True, project="copy")
        )
    assert len(calls) == 2
