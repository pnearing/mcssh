# Contributing

## Getting Started

This project requires Python 3.10 or newer. It has no runtime Python
dependencies.

Run the test suite before submitting a change:

```bash
python -m unittest -v
```

## Changes

- Keep changes focused and compatible with supported Python versions.
- Add or update tests for behavior changes and bug fixes.
- Preserve the command-line interface unless a breaking change is explicitly
  documented.
- Do not include private keys, hostnames, IP addresses, or other credentials
  in commits, issues, or pull requests.

## Pull Requests

Describe the problem, the behavior change, and how you tested it. Keep commit
history and pull requests small enough to review effectively.

Security vulnerabilities should follow the private reporting process in
[SECURITY.md](SECURITY.md), not the public issue tracker.
