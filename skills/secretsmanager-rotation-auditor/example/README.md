# End-to-End Example: Secrets Manager Rotation Audit

A walkthrough showing how to use the `secretsmanager-rotation-auditor` skill
from invocation through remediation. Mirrors the structured-eval pattern of shipping
a concrete worked example per skill.

---

## Scenario

You are preparing for a SOC 2 compliance audit and need to verify the
rotation health of three Secrets Manager secrets before the audit window
closes. The secrets are:

1. **`prod-rds-postgres-credentials`** — production database credentials;
   rotation was never configured.
2. **`analytics-redshift-credentials`** — analytics cluster credentials;
   rotation was enabled but the Lambda was deleted during a cleanup.
3. **`staging-rds-mysql-credentials`** — staging database credentials;
   rotation is configured and appears to be working.

---

## Step 1 — Invoke the skill

### Option A: Slash command

```
/aws:audit-secretsmanager-rotation
```

Then paste the three secret configurations.

### Option B: Natural language

```
You: "Audit these 3 Secrets Manager secrets for rotation health:

  Secret: prod-rds-postgres-credentials
  Type: AWS::RDS::DBInstance
  RotationEnabled: false
  LastRotatedDate: (never)

  Secret: analytics-redshift-credentials
  Type: AWS::Redshift::Cluster
  RotationEnabled: true
  RotationLambdaARN: arn:aws:lambda:us-east-1:123456789012:function:RedshiftRotation
  RotationRules: AutomaticallyAfterDays=60
  LastRotatedDate: 2025-12-15T08:00:00Z
  Lambda State: Deleted (ResourceNotFoundException)

  Secret: staging-rds-mysql-credentials
  Type: AWS::RDS::DBInstance
  RotationEnabled: true
  RotationLambdaARN: arn:aws:lambda:us-east-1:123456789012:function:SecretsManagerRotation-MySQL
  RotationRules: AutomaticallyAfterDays=30
  LastRotatedDate: 2026-07-28T03:15:00Z
  Lambda State: Active, LastInvocation: SUCCESS
"
```

### Option C: CLI routing

```bash
node cli/bin/cli.js route "audit my secrets manager rotation health"
```

Output:

```
[Phase: Audit | Skills routed: secretsmanager-rotation-auditor]

Primary route: secretsmanager-rotation-auditor (score: 18)
```

---

## Step 2 — Skill produces deterministic verdicts

The skill applies its classification logic in dependency-chain order and
emits a per-secret report:

```text
SECRET: prod-rds-postgres-credentials
VERDICT: UNROTATED
REASON: Step 2 (rotation not enabled) — RotationEnabled is false and
        LastRotatedDate has never been set. The PostgreSQL credentials are
        static and have been since creation (180 days ago). CRITICAL for
        RDS database credentials (CIS AWS Foundations Benchmark 1.18).
RISK: CRITICAL
REMEDIATION: Enable rotation with a PostgreSQL rotation Lambda and a 30-day
             interval. Deploy the managed template from Serverless Application
             Repository, then trigger the first rotation manually to verify:
             aws secretsmanager rotate-secret --secret-id prod-rds-postgres-credentials

SECRET: analytics-redshift-credentials
VERDICT: ROTATION_BROKEN
REASON: Step 3b (Lambda deleted) — RotationEnabled is true and the config
        points to RedshiftRotation, but the Lambda function was deleted on
        2026-03-01 (ResourceNotFoundException). Every scheduled rotation
        since then has silently failed. LastRotatedDate (2025-12-15) has not
        advanced in 200+ days. CRITICAL — the rotation config creates a false
        sense of security.
RISK: CRITICAL
REMEDIATION: Recreate the Redshift rotation Lambda from the managed template,
             update the secret's rotation config to point to the new Lambda,
             then trigger a manual rotation to verify. Capture current state
             first:
             aws secretsmanager describe-secret --secret-id analytics-redshift-credentials > /tmp/analytics-backup.json

SECRET: staging-rds-mysql-credentials
VERDICT: OK
REASON: Step 8 — Rotation is enabled, Lambda is Active with correct
        execution-role permissions (SecretsManagerRotation +
        AWSLambdaVPCAccessExecutionRole), last invocation succeeded, no
        AWSPENDING stuck version, and LastRotatedDate (2026-07-28) is within
        the 30-day interval.
RISK: LOW
REMEDIATION: None required. Optionally set up a CloudWatch alarm on
             RotationFailed metric for early detection of future failures.
```

---

## Step 3 — Pipeline integration (Prioritize + Remediate)

When invoked through the orchestrator (`/aws:pipeline`), the findings flow
into the Prioritize and Remediate phases:

```
[Phase: Prioritize | Findings: 2 CRITICAL, 0 HIGH | Skills routed: orchestrator]

1. CRITICAL: prod-rds-postgres-credentials — UNROTATED (static DB password, 180 days)
2. CRITICAL: analytics-redshift-credentials — ROTATION_BROKEN (Lambda deleted, false security)
3. —: staging-rds-mysql-credentials — OK (no action)

[Phase: Remediate | Skills routed: secretsmanager-rotation-auditor]

# Secret 1: Enable rotation (additive, reversible)
aws secretsmanager rotate-secret \
  --secret-id prod-rds-postgres-credentials \
  --rotation-lambda-arn arn:aws:lambda:us-east-1:123456789012:function:SecretsManagerRotation-PostgreSQL \
  --rotation-rules AutomaticallyAfterDays=30

# Secret 2: Recreate Lambda, then rotate (capture state first)
aws secretsmanager describe-secret --secret-id analytics-redshift-credentials > /tmp/analytics-backup-$(date +%s).json
# Deploy new Lambda from SAR template, then:
aws secretsmanager update-secret --secret-id analytics-redshift-credentials \
  --rotation-lambda-arn arn:aws:lambda:us-east-1:123456789012:function:NewRedshiftRotation
aws secretsmanager rotate-secret --secret-id analytics-redshift-credentials
```

---

## Step 4 — Post-remediation verification

Re-run the audit after remediation. Expected output:

```text
SECRET: prod-rds-postgres-credentials
VERDICT: OK
REASON: Step 8 — rotation enabled, Lambda healthy, first rotation succeeded.
REMEDIATION: None required.

SECRET: analytics-redshift-credentials
VERDICT: OK
REASON: Step 8 — new Lambda active, rotation succeeded, LastRotatedDate advanced.
REMEDIATION: None required.

SECRET: staging-rds-mysql-credentials
VERDICT: OK
REASON: Step 8 — unchanged.
REMEDIATION: None required.
```

---

## What the skill catches that a naive review misses

| Secret | Naive review | Skill verdict | Why the skill is right |
|---|---|---|---|
| `prod-rds-postgres-credentials` | "No rotation — should enable it" | UNROTATED / CRITICAL | The skill maps RDS credentials to CRITICAL (CIS 1.18) and provides the exact managed template + interval, not generic "enable rotation" advice. |
| `analytics-redshift-credentials` | "Lambda is deleted" | ROTATION_BROKEN / CRITICAL | The skill distinguishes ROTATION_BROKEN from UNROTATED — broken rotation is riskier because it implies a false sense of security. It also checks that LastRotatedDate hasn't advanced since the Lambda was deleted (200+ days), confirming silent failure. |
| `staging-rds-mysql-credentials` | "Looks healthy" | OK / LOW | The skill doesn't just check RotationEnabled — it verifies the full dependency chain: Lambda state, execution-role policies, VPC config, last invocation status, version stages, and freshness against the interval. The naive review would not check all four links. |

---

## Related artifacts

- **Skill definition:** `skills/secretsmanager-rotation-auditor/SKILL.md`
- **Slash command:** `commands/aws/audit-secretsmanager-rotation.md`
- **Eval suite:** `skills/secretsmanager-rotation-auditor/evals/evals.json`
- **Legacy test cases:** `skills/secretsmanager-rotation-auditor/eval/test-cases.yaml`
