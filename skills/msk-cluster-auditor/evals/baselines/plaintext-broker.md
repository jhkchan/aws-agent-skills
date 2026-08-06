# Baseline (no-skill) response: plaintext-broker

This file captures what a generic assistant produces WITHOUT the
msk-cluster-auditor skill loaded — the contrast that proves the skill
adds structure (deterministic VERDICT, enumerated FINDINGS, specific
remediation, immutability-aware reasoning).

---

This MSK cluster has ClientBroker set to PLAINTEXT, which means traffic
between clients and brokers is not encrypted. You should consider
enabling TLS to protect your data in transit.

The cluster has IAM authentication enabled and logging to CloudWatch,
which is good. It is not publicly accessible.

To fix the encryption issue, you may need to update the cluster
configuration.
