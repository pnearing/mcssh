from pathlib import Path
import shlex
from dataclasses import dataclass

MAX_CLUSTER_LINE_LENGTH = 4096
MAX_HOSTS_PER_LINE = 64
MAX_CLUSTER_HOSTS = 1024
MAX_RESOLVED_HOSTS = 128
MAX_DESTINATION_LENGTH = 512
MAX_IDENTITY_FILE_LENGTH = 4096


@dataclass(frozen=True)
class HostTarget:
    destination: str
    port: str | None = None
    identity_file: str | None = None


def _validate_text(value: str, field: str, maximum_length: int) -> None:
    if not value:
        raise ValueError(f"{field} cannot be empty")
    if len(value) > maximum_length:
        raise ValueError(f"{field} is longer than {maximum_length} characters")
    if any(ord(character) < 32 or 127 <= ord(character) <= 159 for character in value):
        raise ValueError(f"{field} contains a control character")


def validate_destination(destination: str) -> None:
    _validate_text(destination, "SSH destination", MAX_DESTINATION_LENGTH)
    if destination.startswith("-"):
        raise ValueError("SSH destination cannot start with '-'")


def _validate_identity_file(identity_file: str) -> None:
    _validate_text(identity_file, "identity file", MAX_IDENTITY_FILE_LENGTH)


def validate_hosts(hosts: list[HostTarget]) -> None:
    for host in hosts:
        validate_destination(host.destination)
        if host.identity_file is not None:
            identity_file = Path(host.identity_file)
            if not identity_file.is_file():
                raise ValueError(f"identity file is not a readable regular file: {identity_file}")
            try:
                with identity_file.open("rb"):
                    pass
            except OSError as error:
                raise ValueError(
                    f"identity file is not readable: {identity_file}"
                ) from error


def _strip_inline_comment(line: str) -> str:
    """
    Remove everything after #.

    This is simple and deliberate. It means # cannot be used inside hostnames,
    usernames, SSH options, or quoted strings.
    """
    return line.split("#", 1)[0].strip()


def _load_clusters(cluster_file: Path) -> dict[str, list[HostTarget]]:
    clusters: dict[str, list[HostTarget]] = {}
    host_count = 0

    if not cluster_file.exists():
        return clusters

    with cluster_file.open("r", encoding="utf-8") as f:
        for line_number, raw_line in enumerate(f, start=1):
            if len(raw_line) > MAX_CLUSTER_LINE_LENGTH:
                raise ValueError(
                    f"{cluster_file}:{line_number}: line exceeds "
                    f"{MAX_CLUSTER_LINE_LENGTH} characters"
                )
            line = _strip_inline_comment(raw_line)

            if not line:
                continue

            try:
                parts = shlex.split(line)
            except ValueError as e:
                raise ValueError(
                    f"{cluster_file}:{line_number}: could not parse line: {e}"
                ) from e

            cluster_name = parts[0]
            _validate_text(cluster_name, "cluster name", MAX_DESTINATION_LENGTH)
            port: str | None = None
            identity_file: str | None = None
            hosts: list[str] = []
            index = 1

            while index < len(parts):
                part = parts[index]

                if part in ("-p", "--port"):
                    if index + 1 >= len(parts):
                        raise ValueError(
                            f"{cluster_file}:{line_number}: {part} needs a value"
                        )
                    port = parts[index + 1]
                    if not port.isdigit() or not 1 <= int(port) <= 65535:
                        raise ValueError(
                            f"{cluster_file}:{line_number}: invalid port '{port}'"
                        )
                    index += 2
                    continue

                if part in ("-i", "--identity-file"):
                    if index + 1 >= len(parts):
                        raise ValueError(
                            f"{cluster_file}:{line_number}: {part} needs a value"
                        )
                    identity_file = str(Path(parts[index + 1]).expanduser())
                    _validate_identity_file(identity_file)
                    index += 2
                    continue

                if part.startswith("-"):
                    raise ValueError(
                        f"{cluster_file}:{line_number}: unsupported SSH option '{part}'"
                    )

                validate_destination(part)
                hosts.append(part)
                if len(hosts) > MAX_HOSTS_PER_LINE:
                    raise ValueError(
                        f"{cluster_file}:{line_number}: more than "
                        f"{MAX_HOSTS_PER_LINE} hosts on one line"
                    )
                index += 1

            if not hosts:
                raise ValueError(
                    f"{cluster_file}:{line_number}: cluster line needs at least one host"
                )

            clusters.setdefault(cluster_name, []).extend(
                HostTarget(host, port, identity_file) for host in hosts
            )
            host_count += len(hosts)
            if host_count > MAX_CLUSTER_HOSTS:
                raise ValueError(
                    f"{cluster_file}: more than {MAX_CLUSTER_HOSTS} configured hosts"
                )

    return clusters


def resolve_hosts(
    targets: list[str],
    cluster_file: Path,
    cluster_only: bool = False,
) -> list[HostTarget]:
    """
    Resolve command-line targets.

    Cluster lines have the form:
      name [-p PORT] [-i KEYFILE] host [host ...]

    A cluster may be defined on multiple lines. Options apply only to the
    hosts on the line where they occur.

    A target may be:
      - a cluster name from the clusters file
      - a raw SSH host such as root@example.com, unless cluster_only=True

    Examples:
      mcssh.py sitetra
      mcssh.py sitetra root@example.com
      mcssh.py --cluster-only sitetra
    """
    clusters = _load_clusters(cluster_file)

    resolved: list[HostTarget] = []
    unknown_targets: list[str] = []

    for target in targets:
        if target in clusters:
            resolved.extend(clusters[target])
        else:
            if cluster_only:
                unknown_targets.append(target)
            else:
                validate_destination(target)
                resolved.append(HostTarget(target))

        if len(resolved) > MAX_RESOLVED_HOSTS:
            raise ValueError(
                f"more than {MAX_RESOLVED_HOSTS} hosts resolved; split the request"
            )

    if unknown_targets:
        available = ", ".join(sorted(clusters)) or "none"

        raise ValueError(
            "unknown cluster target(s): "
            + ", ".join(unknown_targets)
            + f"\nAvailable clusters: {available}"
        )

    return resolved
