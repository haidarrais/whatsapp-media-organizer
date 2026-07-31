# Security Policy

## Supported versions

Security fixes are released for the latest tagged version of
`whatsapp-media-organizer`.

## Reporting a vulnerability

Please do **not** open a public issue for security problems. Instead, email
the maintainers (address in the GitHub repository sidebar) with:

- A description of the vulnerability and the affected version
- Steps to reproduce
- The impact you believe the issue has

You should receive a response within 5 business days. If you do not, follow up
via a private GitHub security advisory
(https://github.com/OWNER/whatsapp-media-organizer/security/advisories/new).

## Scope

This project only reads and moves media files on the local filesystem. There is
no network surface, no persistence layer, and no user-provided code execution.
That said, reports about unsafe path handling, symlink handling, or anything
that could cause unexpected file loss or access are taken seriously.

## What to include in a report

The most useful reports include a minimal reproduction case, the exact file
names used, and the platform you hit the issue on (Windows / macOS / Linux).
