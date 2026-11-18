# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 2.0.x   | :white_check_mark: |
| < 2.0   | :x:                |

## Air-Gapped & Offline Security Principles

**Face Seeker** is engineered strictly for air-gapped forensic environments:
- **Zero Network Sockets**: The software does not establish outbound network connections or transmit telemetry.
- **Local Loopback IPC**: Inter-process communication between the C# WPF GUI and the Python Computer Vision daemon is strictly bound to `127.0.0.1` (localhost).
- **Read-Only Media Access**: CCTV video files and reference images are opened exclusively in read-only mode to preserve forensic chain-of-custody.

## Reporting a Vulnerability

If you discover a potential security flaw, IPC vulnerability, or memory corruption issue in Face Seeker:
1. Please do **NOT** open a public issue.
2. Email the maintainer directly at **linkwithshivang@gmail.com** with the subject line `[SECURITY] Face Seeker Vulnerability Report`.
3. Include steps to reproduce the issue, proof-of-concept payloads (if applicable), and affected OS/environment details.

We aim to review and acknowledge all responsible disclosures within 48 hours.
