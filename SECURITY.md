# Security Policy

## Supported Versions

Security fixes are made on the latest version in the default branch.

## Reporting a Vulnerability

Use GitHub's private vulnerability-reporting feature for this repository. If
private reporting is unavailable, open a minimal public issue requesting a
private contact channel. Do not include exploit details, credentials, target
addresses, or proof-of-concept payloads in public reports.

Include the affected version, impact, reproduction steps, and any proposed
mitigation. Reports will be assessed and a fix or status update will be
provided as soon as practical.

## Operational Guidance

Keep cluster files writable only by trusted users. Review any changes to SSH
destinations, ports, and identity-file paths before use. Continue to rely on
OpenSSH host-key verification and protect private keys with appropriate file
permissions.
