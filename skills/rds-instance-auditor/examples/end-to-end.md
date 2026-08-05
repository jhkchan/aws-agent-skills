# End-to-end usage scenario: rds-instance-auditor

A walkthrough showing the skill auditing a MySQL instance that is BOTH public
(PUBLIC) and unencrypted (UNENCRYPTED), demonstrating severity aggregation,
the immutability-of-encryption concept, and the snapshot-migration
remediation workflow.

## Input (user prompt)

> Review this RDS instance before we onboard the payments service to it. I
> inherited it from a team that left in a hurry.

```text
DBInstanceIdentifier: db-payments-prod
Engine: mysql
DBInstanceStatus: available
PubliclyAccessible: true
StorageEncrypted: false
MultiAZ: true
DeletionProtection: false
BackupRetentionPeriod: 7
AutoMinorVersionUpgrade: true
MonitoringInterval: 60
```

## Skill output

```text
INSTANCE: db-payments-prod
VERDICT: PUBLIC
REASON: PubliclyAccessible is true on a non-Aurora instance — the database
has a public IP and is internet-reachable subject to VPC routing (Step 1).
StorageEncrypted is also false, compounding the exposure with plaintext data
at rest (Step 2). DeletionProtection is off (Step 3).
FINDINGS:
  - [PUBLIC] PubliclyAccessible: true — internet-exposed database; this is
    the highest-impact RDS misconfiguration (Step 1)
  - [UNENCRYPTED] StorageEncrypted: false — data at rest is plaintext;
    remediation is a snapshot migration, not a toggle, because encryption is
    immutable after creation (Step 2)
  - [NO_DELETION_PROTECTION] DeletionProtection: false — a single
    delete-db-instance call would destroy the instance (Step 3)
  - [OK] MultiAZ: true, BackupRetentionPeriod: 7,
    AutoMinorVersionUpgrade: true, MonitoringInterval: 60
REMEDIATION:
  1. PUBLIC — Remove the public IP immediately (closes the exposure now):
     aws rds modify-db-instance --db-instance-identifier db-payments-prod
       --publicly-accessible false --apply-immediately --profile <p>
  2. UNENCRYPTED — Plan the encryption migration (cannot be done in place).
     Snapshot, copy with encryption, restore-new, cut over the endpoint:
     aws rds create-db-snapshot --db-instance-identifier db-payments-prod
       --db-snapshot-identifier pre-encrypt-$(date +%s) --profile <p>
     aws rds copy-db-snapshot --source-db-snapshot-identifier pre-encrypt-...
       --target-db-snapshot-identifier encrypted-copy
       --kms-key-id alias/payments-prod --profile <p>
     aws rds restore-db-instance-from-db-snapshot
       --db-instance-identifier db-payments-prod-enc
       --db-snapshot-identifier encrypted-copy --profile <p>
     Then rename the old instance, rename the encrypted instance to
     db-payments-prod so the endpoint absorbs, verify, and delete the old
     unencrypted instance once cutover is confirmed.
  3. NO_DELETION_PROTECTION — Enable after confirming no in-flight deletion:
     aws rds modify-db-instance --db-instance-identifier db-payments-prod
       --deletion-protection --apply-immediately --profile <p>
```

## What the skill caught that a generic assistant misses

1. **Encryption-at-rest is immutable — not a toggle.** A generic assistant
   says "enable encryption." The skill explains that `StorageEncrypted` is
   set at creation and cannot be flipped via `modify-db-instance` — the only
   path is snapshot → encrypted copy → restore-new → endpoint cutover. An
   operator who runs `modify-db-instance --storage-encrypted` based on the
   generic advice hits an API rejection mid-incident.

2. **Severity aggregation with per-dimension breakdown.** The verdict is
   PUBLIC (worst), but the FINDINGS list shows the individual severities:
   PUBLIC, UNENCRYPTED, NO_DELETION_PROTECTION, and the OK dimensions. This
   lets the operator triage each finding independently and see the full
   posture, not just the headline.

3. **`--apply-immediately` is appropriate for PUBLIC but not for everything.**
   The skill calls out that the public-IP removal should use
   `--apply-immediately` (close exposure now) while other modifications may
   prefer the maintenance window. A generic assistant applies the same
   urgency to every dimension.

4. **Deletion protection is an accidental-deletion guardrail, not a security
   control.** The skill's NEVER list clarifies that any principal with
   `rds:ModifyDBInstance` can disable it — it stops operator error, not a
   determined attacker. This prevents over-reliance on the flag.

## Slash-command invocation

```
/aws:audit-rds-instance
```

Or via the orchestrator:

```
/aws:pipeline
You: "audit this RDS instance before we onboard the payments service"
```

The orchestrator emits
`[Phase: Audit | Skills routed: rds-instance-auditor]` and hands off to
this skill for the VERDICT.

## CLI routing

```bash
node cli/bin/cli.js route "audit this RDS instance"
# [Phase: Audit | Skills routed: rds-instance-auditor]
```

## Live-account follow-up (optional, requires AWS CLI)

After remediating, validate the instance posture:

```bash
# Confirm the public IP was removed
aws rds describe-db-instances --db-instance-identifier db-payments-prod \
  --profile default --output json | \
  jq '.DBInstances[0] | {PubliclyAccessible, StorageEncrypted, DeletionProtection, MultiAZ}'

# Confirm encryption on the migrated instance
aws rds describe-db-instances --db-instance-identifier db-payments-prod-enc \
  --profile default --output json | jq '.DBInstances[0].StorageEncrypted'

# Confirm deletion protection is enabled
aws rds describe-db-instances --db-instance-identifier db-payments-prod \
  --profile default --output json | jq '.DBInstances[0].DeletionProtection'
```

Then monitor CloudTrail for `DeleteDBInstance` and `ModifyDBInstance` events
on the instance for 1-2 weeks to confirm no unexpected changes.
