# Baseline (no-skill) response: no-encryption-aws-managed

This file captures what a generic assistant produces WITHOUT the
eventbridge-bus-policy-auditor skill loaded — the contrast that proves
the skill adds structure (AWS-owned vs customer-managed key distinction,
decrypt-audit reasoning).

---

The bus policy is well-scoped to same-account principals, and the rule
target has a dead-letter queue. However, no KMS key is configured for
the bus. EventBridge uses a default AWS key for encryption. You should
consider using a customer-managed KMS key for better control.

The archive is also configured which is good.
