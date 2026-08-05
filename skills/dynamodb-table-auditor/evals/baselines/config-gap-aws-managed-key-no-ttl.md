# Baseline (no-skill) response: config-gap-aws-managed-key-no-ttl

This file captures what a generic assistant produces WITHOUT the
dynamodb-table-auditor skill loaded — the contrast that proves the skill
adds structure (deterministic VERDICT, enumerated FINDINGS, specific
remediation, expert knowledge deltas).

---

This table has KMS encryption enabled, PITR on, and on-demand billing, so the
basics are covered. The KMS key is the AWS-managed one which is fine for most
cases. TTL is disabled — you might want to set that up if items should expire.
Deletion protection is off, so consider enabling it.

Overall this table is in decent shape with a few minor improvements.
