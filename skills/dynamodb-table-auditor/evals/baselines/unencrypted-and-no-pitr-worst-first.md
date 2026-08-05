# Baseline (no-skill) response: unencrypted-and-no-pitr-worst-first

This file captures what a generic assistant produces WITHOUT the
dynamodb-table-auditor skill loaded — the contrast that proves the skill
adds structure (deterministic VERDICT, enumerated FINDINGS, specific
remediation, expert knowledge deltas).

---

This table has several issues. The SSE is disabled, so it's using default
encryption without KMS. PITR is also disabled, so there's no recovery if
something goes wrong. TTL is disabled and deletion protection is off. Streams
are not configured either.

You should enable encryption, PITR, and consider the other settings. This table
needs quite a bit of work.
