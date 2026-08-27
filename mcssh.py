#!/usr/bin/env python3

import argparse
import shutil
import sys
from pathlib import Path

from clusters.clusters import(
    resolve_hosts,
    validate_hosts,
)

from tmux.tmux import (
    attach,
    create_session,
    enable_pane_titles,
    send_ssh_command,
    set_pane_title,
    set_sync,
    session_exists,
    split_pane,
    tile_layout,
    kill_session,
    tmux,
)

DEFAULT_SESSION = "mcssh"
DEFAULT_CONFIG_DIR = Path.home().joinpath(".mcssh")
DEFAULT_CLUSTER_FILE = DEFAULT_CONFIG_DIR.joinpath("clusters")
MAX_SESSION_NAME_LENGTH = 64


def validate_session_name(session_name: str) -> None:
    if not session_name:
        raise ValueError("tmux session name cannot be empty")
    if len(session_name) > MAX_SESSION_NAME_LENGTH:
        raise ValueError(
            f"tmux session name is longer than {MAX_SESSION_NAME_LENGTH} characters"
        )
    if any(ord(character) < 32 or 127 <= ord(character) <= 159 for character in session_name):
        raise ValueError("tmux session name contains a control character")


def confirm_session_replacement(session_name: str) -> bool:
    try:
        answer = input(f"Kill existing tmux session '{session_name}'? [y/N] ")
    except (EOFError, KeyboardInterrupt):
        return False
    return answer.lower() in {"y", "yes"}


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Open multiple SSH sessions in tmux panes."
    )

    parser.add_argument(
        "targets",
        nargs="+",
        help="Cluster name(s) or SSH host(s), e.g. mycluster root@example.com",
    )

    parser.add_argument(
        "-s",
        "--session",
        default=DEFAULT_SESSION,
        help=f"tmux session name. Default: {DEFAULT_SESSION}",
    )

    parser.add_argument(
        "-c",
        "--clusters-file",
        type=Path,
        default=DEFAULT_CLUSTER_FILE,
        help=f"Path to clusters file. Default: {DEFAULT_CLUSTER_FILE}",
    )

    parser.add_argument(
        "--no-sync",
        action="store_true",
        help="Disable tmux synchronize-panes.",
    )

    parser.add_argument(
        "--kill-existing",
        action="store_true",
        help="Kill an existing tmux session with the same name before starting.",
    )

    parser.add_argument(
        "--yes",
        action="store_true",
        help="Do not prompt before --kill-existing replaces a session.",
    )

    parser.add_argument(
        "--cluster-only",
        action="store_true",
        help="Require every target to be a cluster name. Unknown targets will error.",
    )

    parser.add_argument(
        "--no-titles",
        action="store_true",
        help="Disable tmux pane titles.",
    )

    args = parser.parse_args()

    try:
        validate_session_name(args.session)
    except ValueError as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1

    if shutil.which("tmux") is None:
        print("Error: tmux is not installed or not in PATH.", file=sys.stderr)
        return 1

    try:
        hosts = resolve_hosts(
            args.targets,
            args.clusters_file,
            cluster_only=args.cluster_only,
        )
        validate_hosts(hosts)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    if not hosts:
        print("Error: no hosts resolved.", file=sys.stderr)
        return 1

    if session_exists(args.session):
        if args.kill_existing:
            if sys.stdin.isatty() and not args.yes:
                if not confirm_session_replacement(args.session):
                    print("Session replacement cancelled.", file=sys.stderr)
                    return 1
            kill_session(args.session)
        else:
            print(
                f"Error: tmux session '{args.session}' already exists.\n"
                f"Use --kill-existing or choose another name with -s.",
                file=sys.stderr,
            )
            return 1

    session_created = False
    try:
        create_session(args.session)
        session_created = True

        if not args.no_titles:
            enable_pane_titles(args.session)
        for index, host in enumerate(hosts):
            if index > 0:
                split_pane(args.session)

            if not args.no_titles:
                set_pane_title(args.session, host.destination)
            send_ssh_command(
                args.session,
                host.destination,
                host.port,
                host.identity_file,
            )
            tile_layout(args.session)

        set_sync(args.session, not args.no_sync)
        attach(args.session)
    except (Exception, KeyboardInterrupt) as e:
        if session_created:
            try:
                tmux("kill-session", "-t", args.session, check=False)
            except Exception:
                pass
        if isinstance(e, KeyboardInterrupt):
            print("Interrupted.", file=sys.stderr)
        else:
            print(f"Error: could not set up tmux session: {e}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
