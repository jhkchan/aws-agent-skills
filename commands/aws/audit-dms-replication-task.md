---
description: Audit a DMS replication task for SSL/TLS gaps on endpoints, missing CDC/task logging, replication instance exposure, endpoint encryption, and task settings integrity.
nl_triggers:
  - "audit this DMS task"
  - "check DMS endpoint SSL"
  - "DMS replication task security"
  - "is my DMS migration encrypted"
  - "DMS CDC logging"
  - "replication instance public"
  - "DMS task settings"
  - "DMS endpoint SSL mode"
  - "DMS migration audit"
  - "hardening DMS replication"
  - "DMS plaintext connection"
  - "replication instance Multi-AZ"
  - "DMS deletion protection"
  - "DMS task validation"
routes_to: dms-replication-task-auditor
---

# /aws:audit-dms-replication-task

Activate the `dms-replication-task-auditor` skill and audit one or more DMS
replication task configurations (task settings + endpoints + instance metadata)
for security exposure.

## What it does

Reads a DMS replication task configuration including endpoint SSL settings,
task logging settings, replication instance metadata, and task-level integrity
controls. Applies the ordered classification logic:

1. TLS / SSL evaluation — source and target endpoint `SslMode`. Missing
   defaults to none (NO_TLS). `require` is CONFIG_GAP (no cert verification).
   `verify-ca`/`verify-full` are OK.
2. Logging evaluation — `TaskSettings` logging enabled? Absent or false is
   NO_LOGGING (silent failures — metrics still show green).
3. Replication instance config — `PubliclyAccessible`, `MultiAZ`, `KmsKeyId`,
   instance class. Each gap is an additive CONFIG_GAP finding.
4. Endpoint encryption and task settings — endpoint `KmsKeyId`, validation
   settings, recovery table, deletion protection.
5. Aggregation — first failing dimension wins (NO_TLS > NO_LOGGING >
   CONFIG_GAP > OK). All findings enumerated.

Emits a deterministic VERDICT per task:

```text
TASK: <task-id>
VERDICT: NO_TLS | NO_LOGGING | CONFIG_GAP | OK
REASON: <1-2 sentences citing the worst finding and step number>
FINDINGS:
  - [NO_TLS] <finding description (Step N)>
  - [CONFIG_GAP] <finding description (Step N)>
REMEDIATION: <specific action per finding, or "None required" if OK>
```

## When to invoke

Paste a DMS replication task configuration and ask any of:

- "audit this DMS replication task"
- "check DMS endpoint SSL/TLS"
- "is my DMS migration encrypted?"
- "is DMS CDC logging enabled?"
- "is my replication instance exposed?"
- "hardening DMS before cutover"

A bare task ARN or endpoint reference + any audit verb also routes here.

## Inputs

- A DMS replication task configuration: task settings (JSON string), source
  endpoint config, target endpoint config, and replication instance metadata.
- For S3 targets: the source endpoint SslMode is evaluated; the S3 target is
  exempt from SslMode checks (HTTPS enforced by SDK).

## Outputs

- One VERDICT block per task (multiple findings aggregate by priority —
  NO_TLS > NO_LOGGING > CONFIG_GAP > OK).
- Enumerated FINDINGS list with per-finding classification and step citation.
- Specific remediation: modify endpoint SslMode, enable task logging, make
  instance private, enable Multi-AZ, add KMS keys, enable validation.

## Related

- `/aws:pipeline` to enter the full CloudOps pipeline (this skill is the
  Phase 2 Audit specialist for DMS migration security).
- `/aws:audit-kms-key-policy` for auditing the KMS keys used by DMS
  endpoints and replication instances.
