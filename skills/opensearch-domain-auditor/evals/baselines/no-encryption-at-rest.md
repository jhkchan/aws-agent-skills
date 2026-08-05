# Baseline (no-skill) response: no-encryption-at-rest

This file captures what a generic assistant produces WITHOUT the
opensearch-domain-auditor skill loaded — the contrast that proves the skill
adds structure (deterministic VERDICT, enumerated FINDINGS, specific
remediation, immutability reasoning).

---

This OpenSearch domain does not have encryption at rest enabled. That means
the data stored on disk is plaintext, which is a compliance issue for most
regulated workloads.

You should enable encryption at rest on this domain. The rest of the
configuration looks reasonable — node-to-node encryption is on, fine-grained
access control is on, dedicated masters are properly sized, and slow logs
are being published to CloudWatch.

The access policy only allows same-account principals, which is fine.
