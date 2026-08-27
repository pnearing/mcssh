# Agent Notes

## Verification

- Run the complete suite with `python -m unittest -v`.
- Run one test with `python -m unittest test_mcssh.TmuxTests.test_ssh_command_is_escaped_and_targeted`.
- CI runs that same suite on Python 3.10 through 3.14; keep code compatible with the full matrix.

## Structure

- `mcssh.py` is both the CLI entry point and the installed `mcssh` console script.
- `clusters/clusters.py` parses and validates cluster configuration; `tmux/tmux.py` is the subprocess wrapper for tmux and constructs the SSH command.
- Package metadata explicitly ships root module `mcssh` and the `clusters` and `tmux` packages. Update `pyproject.toml` if adding another importable package.

## Security-Sensitive Paths

- Preserve `shlex.quote()` and the `--` before the SSH destination in `send_ssh_command`; both prevent destination input from becoming SSH options or shell syntax.
- Preserve input limits, control-character validation, and pane-title sanitization when changing cluster resolution or tmux display code.
- `--kill-existing` must retain its interactive confirmation behavior; `--yes` is the explicit non-interactive bypass.

## Test Quirk

- `tmux/__init__.py` exports a function named `tmux`, which shadows the `tmux.tmux` submodule for string-based mock resolution on Python 3.10. Tests that mock the submodule must import it with `importlib.import_module("tmux.tmux")` and use `patch.object`.
