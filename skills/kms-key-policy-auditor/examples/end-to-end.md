# End-to-end usage scenario: kms-key-policy-auditor

A walkthrough showing the skill auditing a KMS key that has both a
cross-account decrypt grant (CRITICAL) and disabled rotation (HIGH),
demonstrating severity aggregation, the blast-radius-multiplier concept,
and the assume-breach remediation workflow.

## Input (user prompt)

> Review this KMS key policy before we attach it to the production data
> warehouse. The key encrypts RDS snapshots and S3 data lake objects.

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "RootAccess",
      "Effect": "Allow",
      "Principal": {"AWS": "arn:aws:iam::111111111111:root"},
      "Action": "kms:*",
      "Resource": "*"
    },
    {
      "Sid": "PartnerDecrypt",
      "Effect": "Allow",
      "Principal": {"AWS": "arn:aws:iam::999999999999:role/partner-analytics"},
      "Action": [
        "kms:Decrypt",
        "kms:DescribeKey"
      ],
      "Resource": "*"
    },
    {
      "Sid": "AppAccess",
      "Effect": "Allow",
      "Principal": {"AWS": "arn:aws:iam::111111111111:role/app-etl-role"},
      "Action": [
        "kms:Encrypt",
        "kms:Decrypt",
        "kms:GenerateDataKey*",
        "kms:DescribeKey"
      ],
      "Resource": "*",
      "Condition": {
        "StringEquals": {
          "kms:ViaService": "s3.us-east-1.amazonaws.com"
        }
      }
    }
  ]
}
```

Key metadata:
- KeyManager: CUSTOMER
- KeySpec: SYMMETRIC_DEFAULT
- Origin: AWS_KMS
- KeyState: Enabled
- EnableKeyRotation: false

## Skill output

```text
KEY: arn:aws:kms:us-east-1:111111111111:key/prod-dw-key
VERDICT: CRITICAL
REASON: Statement "PartnerDecrypt" grants kms:Decrypt to a cross-account
principal (999999999999) with no restrictive condition — the external account
can read all ciphertext encrypted under this key, including every RDS snapshot
and S3 data lake object (Rule 5c). Rotation is also disabled on a
customer-managed symmetric key, compounding the exposure.
FINDINGS:
  - [CRITICAL] Cross-account kms:Decrypt to 999999999999:role/partner-analytics
    with no condition (Rule 5c) — blast-radius multiplier: one permission,
    full encrypted-data exposure
  - [HIGH] EnableKeyRotation is false on a customer-managed SYMMETRIC_DEFAULT
    key (Step 6) — key material never rotates; compromise is permanent
  - [OK] Statement "AppAccess" — same-account role with kms:ViaService condition
    restricting to S3 (Rule 5l + Rule 5k)
  - [OK] Statement "RootAccess" — normal root-of-trust delegation to IAM
REMEDIATION:
  1. CRITICAL — Remove the "PartnerDecrypt" statement immediately. If
     cross-account decrypt is genuinely required, replace Principal "*"
     with the specific role ARN AND add aws:SourceAccount +
     aws:SourceArn conditions.
  2. CRITICAL — Assume breach. Audit CloudTrail for kms:Decrypt calls from
     999999999999 during the exposure window. Re-encrypt all affected RDS
     snapshots and S3 objects under a new key with a clean policy.
  3. HIGH — Enable rotation: aws kms enable-key-rotation --key-id prod-dw-key.
  4. Back up the current policy before changes:
     aws kms get-key-policy --key-id prod-dw-key --policy-name default
     --output json > /tmp/prod-dw-key-policy-backup.json.
```

## What the skill caught that a generic assistant misses

1. **The kms:Decrypt blast-radius multiplier.** A generic assistant says
   "cross-account access is risky." The skill explains that
   `kms:Decrypt` is not one permission on one resource — it grants read
   access to EVERY ciphertext encrypted under the key, across every
   service (RDS, S3, EBS, Secrets Manager). One grant, total data
   exposure.

2. **The root-of-trust statement is NOT flagged.** The `Principal: root`
   + `kms:*` statement is the default IAM-delegation pattern. A naive
   auditor flags it as "wildcard kms:* access." The skill recognises it
   as NORMAL (Rule 5l special case) and excludes it from the verdict.

3. **Severity aggregation with per-finding breakdown.** The verdict is
   CRITICAL (worst finding), but the FINDINGS list shows the individual
   severities: the cross-account decrypt is CRITICAL, the rotation gap
   is HIGH, and the app-access statement is OK. This lets the operator
   triage each finding independently.

4. **The assume-breach remediation workflow.** Generic advice says
   "remove the access." The skill's remediation includes auditing
   CloudTrail for decrypt events during the exposure window and
   re-encrypting affected data — because the ciphertext may have already
   been exfiltrated.

## Slash-command invocation

```
/aws:audit-kms-key-policy
```

Or via the orchestrator:

```
/aws:pipeline
You: "audit this KMS key policy before we use it for the data warehouse"
```

The orchestrator emits
`[Phase: Audit | Skills routed: kms-key-policy-auditor]` and hands off
to this skill for the VERDICT.

## CLI routing

```bash
node cli/bin/cli.js route "audit this KMS key policy"
# [Phase: Audit | Skills routed: kms-key-policy-auditor]
```

## Live-account follow-up (optional, requires AWS CLI)

After remediating the policy, validate the key posture:

```bash
# Verify the cross-account principal was removed
aws kms get-key-policy --key-id prod-dw-key --policy-name default \
  --profile default --output json | jq '.Statement[] | .Principal'

# Confirm rotation is enabled
aws kms get-key-rotation-status --key-id prod-dw-key --profile default

# Check for any lingering grants created by the exposed principal
aws kms list-grants --key-id prod-dw-key --profile default
```

Then monitor CloudTrail for `kms:Decrypt` events from unexpected
principles for 1-2 weeks.
