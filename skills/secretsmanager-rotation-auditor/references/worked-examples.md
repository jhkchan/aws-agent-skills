# Worked Examples — Secrets Manager Rotation Auditor

> Moved verbatim from SKILL.md for progressive disclosure (agentskills.io). Load on demand.

### Replica pre-flight emit block (OK — read-only replica)

```text
SECRET: <name>
VERDICT: OK
REASON: Replica secret (PrimaryRegion: <region>). Rotation runs on the
        primary; the replica inherits the rotated value automatically.
        Audit the primary secret in <PrimaryRegion> for rotation posture.
RISK: LOW
REMEDIATION: None required on the replica. Verify rotation health on the
             primary secret in region <PrimaryRegion>.
```

### DELETION_FLAG emit block (recovery window)

```text
DELETION_FLAG: Secret "<name>" is in the recovery window (DeletedDate:
<date>, scheduled permanent deletion in <N> days). If this secret is still
used by any workload, restore it immediately: aws secretsmanager
restore-secret --secret-id <name>. If deletion is intentional, verify no
application references it before the purge date.
```

### Null LastRotatedDate, rotation enabled multiple intervals (ROTATION_BROKEN)

**Null LastRotatedDate with rotation enabled for multiple intervals (DeletedDate absent):**
```text
SECRET: legacy-oracle-credentials
VERDICT: ROTATION_BROKEN
REASON: Step 7a — RotationEnabled is true but LastRotatedDate is null and
        rotation has been enabled for ~90 days (3x the 30-day interval).
        Every scheduled rotation has silently failed. The Lambda's last
        invocation errored with ResourceNotFoundException — the target RDS
        instance was deleted on 2026-06-15.
RISK: HIGH
REMEDIATION: The target RDS instance is deleted — the Lambda cannot rotate
             against a non-existent database. Either delete the orphaned
             secret or retarget it to the replacement instance, then
             trigger a manual rotation to verify.
```

