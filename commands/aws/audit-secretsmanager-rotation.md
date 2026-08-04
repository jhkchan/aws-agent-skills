---
description: Audit a Secrets Manager secret for rotation health — rotation enablement, Lambda health, staleness, and recovery-window state.
nl_triggers:
  - "is this secret rotating"
  - "check secret rotation"
  - "secret rotation health"
  - "rotation lambda broken"
  - "stale secret"
  - "unrotated secret"
  - "LastRotatedDate"
  - "AutomaticallyAfterDays"
  - "AWSPENDING stuck"
  - "recovery window secret"
  - "credential hygiene"
  - "rotation compliance"
  - "RDS credentials rotation"
  - "API token rotation"
  - "secretsmanager audit"
routes_to: secretsmanager-rotation-auditor
---

# /aws:audit-secretsmanager-rotation

Activate the `secretsmanager-rotation-auditor` skill and classify one or more
Secrets Manager secrets for rotation health and credential hygiene.

## What it does

Reads a Secrets Manager secret's configuration (describe-secret output +
optional Lambda function state) and applies the 8-step classification logic
in dependency-chain order:

1. Recovery-window / deletion check (emit DELETION_FLAG if DeletedDate set).
2. Rotation not enabled -> UNROTATED (risk by secret type: CRITICAL for RDS/Redshift, HIGH for API tokens).
3. Lambda existence and state (deleted/404, inactive, cross-region) -> ROTATION_BROKEN.
4. Lambda invocation health (last invocation error code and root cause) -> ROTATION_BROKEN.
5. Execution-role permission chain (Secrets Manager API, KMS decrypt, VPC access, target credential match) -> ROTATION_BROKEN if any link broken.
6. AWSPENDING stuck version (rotation failed mid-flight) -> ROTATION_BROKEN.
7. Freshness / staleness (null LastRotatedDate after 1+ interval, overdue ratio) -> ROTATION_BROKEN or STALE.
8. Within schedule + Lambda healthy -> OK.

Emits a deterministic VERDICT per secret:

```text
SECRET: <name>
VERDICT: UNROTATED | ROTATION_BROKEN | STALE | OK
REASON: <1-2 sentences citing the specific config and which step fired>
RISK: CRITICAL | HIGH | MODERATE | LOW
REMEDIATION: <specific action, or "None required" if OK>
```

## When to invoke

Paste a secret's describe-secret output (and optional Lambda function state)
and ask any of:

- "is this secret actually rotating?"
- "check rotation health"
- "why did rotation stop working?"
- "is this credential stale?"
- "audit my secrets for compliance"
- "is the rotation Lambda broken?"

A bare secret name + any audit verb ("audit this secret", "check rotation")
also routes here via the orchestrator.

## Inputs

- A Secrets Manager secret config (paste `describe-secret` output inline, or
  describe the fields: RotationEnabled, RotationLambdaARN, RotationRules,
  LastRotatedDate, DeletedDate, VersionIdsToStages).
- Optional: the rotation Lambda function state (State, Role, RolePolicies,
  Timeout, VpcConfig, LastInvocation) for health checks.
- Optional: KMS key ID for the decrypt-permission chain check.

## Outputs

- One VERDICT block per secret (multiple secrets aggregate to the worst
  verdict).
- DELETION_FLAG if the secret is in the recovery window.
- Specific remediation: enable rotation, fix Lambda permissions, clear
  stuck AWSPENDING, increase timeout, restore deleted secret, etc.

## Related

- `/aws:pipeline` to enter the full CloudOps pipeline (this skill is the
  Phase 2 Audit specialist for Secrets Manager).
- `references/policy-analysis-guide.md` on the IAM skill for scoping the
  rotation Lambda execution role.
