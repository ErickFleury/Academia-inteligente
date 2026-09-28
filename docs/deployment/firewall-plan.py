#!/usr/bin/env python3
"""Print Docker-aware firewall commands; never modify the host firewall."""

import argparse
import ipaddress
import re
import shlex


def render(interface: str, management_network: str, ssh_port: int) -> str:
    if not re.fullmatch(r"[A-Za-z0-9_.:-]{1,32}", interface):
        raise ValueError("Invalid public interface")
    network = ipaddress.ip_network(management_network, strict=True)
    if network.prefixlen == 0:
        raise ValueError("The management network must not allow the whole Internet")
    if not 1 <= ssh_port <= 65535 or ssh_port in {80, 443}:
        raise ValueError("Invalid SSH port")
    interface = shlex.quote(interface)
    commands = [
        "# Review in a maintenance window with working out-of-band console access.",
        "# Never run this through an SSH connection outside the management network.",
        "# Apply equivalent provider firewall restrictions before exposing this host.",
        "# Requires Linux Docker's iptables backend, UFW and IPv6 filtering enabled.",
        "# Do not disable Docker's firewall management or merge nftables examples.",
        "# Confirm the interface carries ALL public ingress (repeat for other interfaces).",
        "sudo ufw status verbose",
        "sudo iptables -S DOCKER-USER",
        "sudo ip6tables -S DOCKER-USER",
        "# STOP if either chain check fails; adapt the plan to the host before continuing.",
        "# Remove any pre-existing broad allow rules after reviewing them.",
        "sudo ufw default deny incoming",
        "sudo ufw default allow outgoing",
        f"sudo ufw allow from {network} to any port {ssh_port} proto tcp",
        "sudo ufw allow 80/tcp",
        "sudo ufw allow 443/tcp",
        "sudo ufw enable",
        "# Docker forwarding requires separate rules; UFW alone is insufficient.",
    ]
    for tool in ["iptables", "ip6tables"]:
        commands.extend(
            [
                f"sudo {tool} -N ACADEMIA-INGRESS",
                f"sudo {tool} -A ACADEMIA-INGRESS -i {interface} "
                "-m conntrack --ctstate ESTABLISHED,RELATED -j RETURN",
                f"sudo {tool} -A ACADEMIA-INGRESS -i {interface} -p tcp "
                "-m conntrack --ctorigdstport 80 -j RETURN",
                f"sudo {tool} -A ACADEMIA-INGRESS -i {interface} -p tcp "
                "-m conntrack --ctorigdstport 443 -j RETURN",
                f"sudo {tool} -A ACADEMIA-INGRESS -i {interface} -j DROP",
                f"sudo {tool} -A ACADEMIA-INGRESS -j RETURN",
                f"sudo {tool} -I DOCKER-USER 1 -j ACADEMIA-INGRESS",
            ]
        )
    commands.extend(
        [
            "# Install once; do not append duplicate chains/rules on subsequent runs.",
            "# Persist using the host's firewall tooling, AFTER Docker creates DOCKER-USER.",
            "# Re-verify IPv4 and IPv6 after a reboot and after Docker/host updates.",
            "# From an external machine, verify only 80/443 and restricted SSH are reachable.",
            "# Rollback: remove the DOCKER-USER jumps before flushing/deleting our chain.",
            "# Restore the recorded pre-change UFW policy through the out-of-band console.",
        ]
    )
    return "\n".join(commands) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--interface", required=True)
    parser.add_argument("--management-network", required=True)
    parser.add_argument("--ssh-port", type=int, default=22)
    args = parser.parse_args()
    try:
        print(render(args.interface, args.management_network, args.ssh_port), end="")
    except ValueError as error:
        parser.error(str(error))


if __name__ == "__main__":
    main()
