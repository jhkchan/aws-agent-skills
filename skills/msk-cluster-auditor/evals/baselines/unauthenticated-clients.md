# Baseline (no-skill) response: unauthenticated-clients

This file captures what a generic assistant produces WITHOUT the
msk-cluster-auditor skill loaded — the contrast that proves the skill
adds structure (deterministic VERDICT, enumerated FINDINGS, specific
remediation, immutability-aware reasoning).

---

The cluster has TLS encryption enabled for both client-broker and
in-cluster communication, which is good. However, unauthenticated access
is enabled, meaning clients can connect without any credentials.

You should disable unauthenticated access and rely on the SASL/IAM
authentication that is already configured. The cluster is not publicly
accessible and has CloudWatch logging enabled.
