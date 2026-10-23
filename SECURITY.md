# Security policy

## Scope

WarpCoil 1.3.1 is a local-network beta. It is **not designed for untrusted networks**.

- Traffic uses plain HTTP and is **not encrypted**. The six-digit pairing PIN is not a substitute for transport encryption.
- Anybody with sufficient access to your LAN might observe or interfere with transfers. Do not transfer sensitive files on untrusted networks.
- Never expose port 8765 to the internet and never configure router port forwarding for WarpCoil.
- Allow access only on private/trusted networks; close the program when not actively used.
- Treat incoming files as untrusted content and scan them before opening them.

## Reporting vulnerabilities

Until a private reporting channel is configured on the public repository, do not post exploitable security details in a public GitHub issue. Contact the maintainer privately through GitHub profile contact details if available.

Security hardening and an authenticated encrypted transport remain roadmap items. This code has not received an independent security audit.
