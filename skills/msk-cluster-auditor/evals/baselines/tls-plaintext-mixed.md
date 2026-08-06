# Baseline (no-skill) response: tls-plaintext-mixed

This file captures what a generic assistant produces WITHOUT the
msk-cluster-auditor skill loaded — the contrast that proves the skill
adds structure (deterministic VERDICT, enumerated FINDINGS, specific
remediation, immutability-aware reasoning).

---

This cluster has TLS_PLAINTEXT for ClientBroker, which means it supports
both TLS and plaintext connections. It also has TLS certificate auth and
IAM SASL enabled, with unauthenticated disabled. Logging to S3 is on.

Since TLS is available, clients can choose to use encrypted connections.
You might want to enforce TLS-only mode by switching to ClientBroker: TLS
to prevent any plaintext traffic.
