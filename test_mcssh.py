import tempfile
import unittest
import sys
from pathlib import Path
from unittest.mock import patch

from clusters.clusters import MAX_RESOLVED_HOSTS, HostTarget, resolve_hosts, validate_hosts
from tmux.tmux import send_ssh_command, set_pane_title
import mcssh


class ClusterTests(unittest.TestCase):
    def resolve(self, contents: str, targets: list[str]) -> list[HostTarget]:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8") as file:
            file.write(contents)
            file.flush()
            return resolve_hosts(targets, Path(file.name))

    def test_repeated_cluster_lines_keep_line_options(self) -> None:
        hosts = self.resolve(
            "production -p 2221 -i ~/first_key host1 host2\n"
            "production -p 2222 -i ~/second_key host3 host4\n"
            "production host5\n",
            ["production"],
        )

        self.assertEqual(
            hosts,
            [
                HostTarget("host1", "2221", str(Path("~/first_key").expanduser())),
                HostTarget("host2", "2221", str(Path("~/first_key").expanduser())),
                HostTarget("host3", "2222", str(Path("~/second_key").expanduser())),
                HostTarget("host4", "2222", str(Path("~/second_key").expanduser())),
                HostTarget("host5"),
            ],
        )

    def test_options_are_optional(self) -> None:
        self.assertEqual(
            self.resolve("one -p 22 host1\ntwo -i key host2\nthree host3\n", ["one", "two", "three"]),
            [HostTarget("host1", "22"), HostTarget("host2", identity_file="key"), HostTarget("host3")],
        )

    def test_unsupported_option_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "unsupported SSH option"):
            self.resolve("production -q host1\n", ["production"])

    def test_option_like_raw_destination_is_rejected(self) -> None:
        with tempfile.NamedTemporaryFile() as file:
            with self.assertRaisesRegex(ValueError, "cannot start"):
                resolve_hosts(["-oProxyCommand=malicious"], Path(file.name))

    def test_control_characters_in_config_are_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "control character"):
            self.resolve("production host\x1b[31m\n", ["production"])

    def test_resolved_host_count_is_limited(self) -> None:
        with tempfile.NamedTemporaryFile() as file:
            with self.assertRaisesRegex(ValueError, "hosts resolved"):
                resolve_hosts(
                    [f"host{index}" for index in range(MAX_RESOLVED_HOSTS + 1)],
                    Path(file.name),
                )

    def test_identity_file_must_exist_and_be_readable(self) -> None:
        with self.assertRaisesRegex(ValueError, "identity file"):
            validate_hosts([HostTarget("host1", identity_file="/does/not/exist")])

        with tempfile.NamedTemporaryFile() as file:
            validate_hosts([HostTarget("host1", identity_file=file.name)])


class TmuxTests(unittest.TestCase):
    @patch("tmux.tmux.tmux")
    def test_ssh_command_is_escaped_and_targeted(self, tmux):
        send_ssh_command("mcssh", "user@host; touch /tmp/pwned", "2222", "/tmp/key file")

        tmux.assert_called_once_with(
            "send-keys",
            "-t",
            "mcssh:0",
            "ssh -p 2222 -i '/tmp/key file' -- 'user@host; touch /tmp/pwned'",
            "C-m",
        )

    @patch("tmux.tmux.tmux")
    def test_pane_title_strips_terminal_controls_and_is_bounded(self, tmux):
        set_pane_title("mcssh", "host\x1b[31m\n" + "a" * 300)

        tmux.assert_called_once_with(
            "select-pane",
            "-t",
            "mcssh:0",
            "-T",
            "host[31m" + "a" * 248,
        )

    @patch.object(mcssh, "tmux")
    @patch.object(mcssh, "enable_pane_titles", side_effect=RuntimeError("setup failed"))
    @patch.object(mcssh, "create_session")
    @patch.object(mcssh, "session_exists", return_value=False)
    @patch.object(mcssh.shutil, "which", return_value="/usr/bin/tmux")
    def test_setup_failure_removes_created_session(
        self, _which, _exists, create_session, _titles, tmux
    ):
        with patch.object(sys, "argv", ["mcssh.py", "host1"]):
            self.assertEqual(mcssh.main(), 1)

        create_session.assert_called_once_with("mcssh")
        tmux.assert_called_once_with("kill-session", "-t", "mcssh", check=False)

    @patch.object(mcssh, "create_session")
    @patch.object(mcssh, "session_exists", return_value=True)
    @patch.object(mcssh, "kill_session")
    @patch.object(mcssh, "confirm_session_replacement", return_value=False)
    @patch.object(mcssh.shutil, "which", return_value="/usr/bin/tmux")
    def test_existing_session_requires_interactive_confirmation(
        self, _which, _confirm, kill_session, _exists, create_session
    ):
        with patch.object(sys, "argv", ["mcssh.py", "--kill-existing", "host1"]):
            with patch.object(mcssh.sys.stdin, "isatty", return_value=True):
                self.assertEqual(mcssh.main(), 1)

        kill_session.assert_not_called()
        create_session.assert_not_called()

    @patch.object(mcssh, "create_session")
    @patch.object(mcssh, "session_exists", return_value=False)
    @patch.object(mcssh.shutil, "which", return_value="/usr/bin/tmux")
    def test_invalid_session_name_never_creates_a_session(
        self, _which, _exists, create_session
    ):
        with patch.object(sys, "argv", ["mcssh.py", "-s", "bad\x1bname", "host1"]):
            self.assertEqual(mcssh.main(), 1)

        create_session.assert_not_called()


if __name__ == "__main__":
    unittest.main()
