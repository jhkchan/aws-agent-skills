# Baseline (no-skill) response: no-fgac-internet-exposed

This file captures what a generic assistant produces WITHOUT the
opensearch-domain-auditor skill loaded.

---

This OpenSearch domain looks mostly well-configured. It has customer-managed
KMS encryption at rest, node-to-node encryption on, and the access policy
is scoped to specific same-account IAM roles rather than a wildcard.

The one gap is that fine-grained access control (Advanced Security) is not
enabled. Without FGAC, the role granted es:ESHttp* in the policy can access
all indices — there is no per-index or per-role enforcement. You should
enable Advanced Security if you need finer-grained access control.

The rest of the configuration is healthy.
