# Error handling — rds-instance-auditor (load on demand)

Moved verbatim from SKILL.md; load only when needed.

## Concrete error-handling example — malformed metadata

When the input is missing required fields (no `DBInstanceIdentifier`, absent
`Engine`, or unparseable JSON), the skill MUST emit a single deterministic
ERROR block and NOT attempt partial classification:

```text
INSTANCE: <identifier or unknown>
VERDICT: ERROR
REASON: RDS instance metadata is missing required fields (DBInstanceIdentifier, Engine) — cannot classify.
FINDINGS:
  - [ERROR] Missing field: <field-name>. Re-fetch with `aws rds describe-db-instances --db-instance-identifier <id> --output json`.
REMEDIATION: Re-fetch metadata and re-audit. If the identifier is unknown, list instances first with `aws rds describe-db-instances --query 'DBInstances[*].DBInstanceIdentifier' --output text`.
```

For a field that is present but has an unexpected TYPE (e.g.,
`BackupRetentionPeriod` as a string instead of integer), emit the same ERROR
block with `[ERROR] Type mismatch on <field>: expected <type>, got <value>`.
Do NOT coerce silently — surface the discrepancy so the operator knows the
input is malformed.

