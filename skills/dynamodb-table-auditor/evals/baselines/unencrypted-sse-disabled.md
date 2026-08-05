# Baseline (no-skill) response: unencrypted-sse-disabled

This file captures what a generic assistant produces WITHOUT the
dynamodb-table-auditor skill loaded — the contrast that proves the skill
adds structure (deterministic VERDICT, enumerated FINDINGS, specific
remediation, expert knowledge deltas).

---

This DynamoDB table has SSE disabled, which means it's using the default
encryption. You should enable KMS encryption for better security. The table
has on-demand billing which is fine, and PITR is enabled which is good.
Deletion protection is on. TTL is configured.

To fix the encryption, update the table with SSE specification.
