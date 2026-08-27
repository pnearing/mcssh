import subprocess
import shlex

MAX_PANE_TITLE_LENGTH = 256


def run(cmd: list[str], check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, check=check)


def tmux(*args: str, check: bool = True) -> subprocess.CompletedProcess:
    return run(["tmux", *args], check=check)


def session_exists(session_name: str) -> bool:
    result = subprocess.run(
        ["tmux", "has-session", "-t", session_name],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return result.returncode == 0


def kill_session(session_name: str) -> None:
    tmux("kill-session", "-t", session_name)


def create_session(session_name: str) -> None:
    tmux("new-session", "-d", "-s", session_name)


def send_ssh_command(
    session_name: str,
    destination: str,
    port: str | None = None,
    identity_file: str | None = None,
) -> None:
    args = ["ssh"]
    if port is not None:
        args.extend(["-p", port])
    if identity_file is not None:
        args.extend(["-i", identity_file])
    # Do not allow a destination beginning with '-' to be parsed as an SSH option.
    args.extend(["--", destination])
    command = " ".join(shlex.quote(arg) for arg in args)
    tmux("send-keys", "-t", f"{session_name}:0", command, "C-m")


def split_pane(session_name: str) -> None:
    tmux("split-window", "-t", f"{session_name}:0", "-h")


def tile_layout(session_name: str) -> None:
    tmux("select-layout", "-t", f"{session_name}:0", "tiled")


def set_sync(session_name: str, enabled: bool) -> None:
    value = "on" if enabled else "off"
    tmux("set-window-option", "-t", f"{session_name}:0", "synchronize-panes", value)


def set_pane_title(session_name: str, title: str) -> None:
    safe_title = "".join(
        character
        for character in title
        if ord(character) >= 32 and not 127 <= ord(character) <= 159
    )[:MAX_PANE_TITLE_LENGTH]
    tmux("select-pane", "-t", f"{session_name}:0", "-T", safe_title)
    

def enable_pane_titles(session_name: str) -> None:
    target = f"{session_name}:0"
    tmux("set-window-option", "-t", target, "pane-border-status", "top")
    tmux("set-window-option", "-t", target, "pane-border-format", " #{pane_title} ")
    tmux("set-window-option", "-t", target, "pane-border-style", "fg=white")
    tmux("set-window-option", "-t", target, "pane-active-border-style", "fg=green,bold")

def attach(session_name: str) -> None:
    tmux("attach-session", "-t", session_name)
