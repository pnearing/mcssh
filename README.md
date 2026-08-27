# mcssh

`mcssh` opens SSH connections to multiple targets in a tiled tmux window.
It supports named clusters, per-cluster SSH ports and identity files, pane
titles, and synchronized input across panes.

## Requirements

- Python 3.10 or newer
- `tmux`
- OpenSSH client (`ssh`)

## Installation

Clone the repository and install it into an environment of your choice:

```bash
python -m pip install .
```

Run it with the installed command:

```bash
mcssh web-01 admin@db-01
```

Alternatively, run the checkout directly:

```bash
python mcssh.py web-01 admin@db-01
```

## Cluster Configuration

By default, clusters are read from `~/.mcssh/clusters`. Use
`--clusters-file PATH` to select another file.

Each non-comment line has this form:

```text
name [-p PORT] [-i IDENTITY_FILE] host [host ...]
```

For example:

```text
# Production application servers
production -p 22 -i ~/.ssh/production_ed25519 deploy@app-01 deploy@app-02

# A second cluster can use different connection settings.
staging -p 2222 deploy@staging-01
```

Run a cluster by name:

```bash
mcssh production
```

Cluster definitions may span multiple lines. Options apply only to hosts on
the line where they are defined.

## Usage

```text
usage: mcssh [-h] [-s SESSION] [-c CLUSTERS_FILE] [--no-sync]
             [--kill-existing] [--yes] [--cluster-only] [--no-titles]
             targets [targets ...]
```

- `-s`, `--session`: Set the tmux session name. The default is `mcssh`.
- `-c`, `--clusters-file`: Select a cluster configuration file.
- `--no-sync`: Disable synchronized input between panes.
- `--kill-existing`: Replace an existing session with the chosen name. This
  prompts for confirmation in an interactive terminal.
- `--yes`: Skip the replacement prompt when using `--kill-existing`; useful
  for automation.
- `--cluster-only`: Reject raw SSH destinations and require cluster names.
- `--no-titles`: Disable tmux pane titles.

## Security

`mcssh` preserves OpenSSH's normal host-key verification behavior. Manage
trusted hosts through your SSH configuration and `known_hosts` files.

The program terminates SSH option parsing before every destination, validates
configuration input, bounds cluster sizes, and removes control characters from
pane titles. Treat cluster files as trusted configuration: they determine
which systems the invoking user connects to and which identity files are used.

See [SECURITY.md](SECURITY.md) for vulnerability reporting guidance.

## Development

The project has no runtime Python dependencies. Run the test suite with:

```bash
python -m unittest -v
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for contribution guidance.

## License

This project is licensed under the GNU General Public License v3.0 only. See
[LICENSE](LICENSE).
