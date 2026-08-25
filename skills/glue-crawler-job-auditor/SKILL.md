---
name: glue-crawler-job-auditor
description: Audits AWS Glue crawlers and jobs (plus their data-catalog encryption, JDBC connections, IAM execution roles, security configurations, job bookmarks, and S3 source encryption) for data-at-rest exposure, over-permissive pass-role blast radius, and configuration gaps. Emits a deterministic verdict — NO_ENCRYPTION | OVERPERMISSIVE_ROLE | CONFIG_GAP | OK — per crawler or job with enumerated findings and CLI remediation. Use when reviewing Glue crawlers/jobs before production, checking catalog encryption, validating JDBC SSL, tightening the execution role, or hardening ETL security posture.
license: Apache-2.0
compatibility: Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). No AWS CLI required for offline config classification. Live-account audits use aws glue get-data-catalog-encryption-settings, get-security- configuration, get-job, get-crawler, get-connection, and aws s3api get-bucket-encryption (AWS CLI v2, SSO or key-based credentials).
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: 'true'
  phase: '2'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: Analytics
  verdict_shape: NO_ENCRYPTION | OVERPERMISSIVE_ROLE | CONFIG_GAP | OK
  when_to_use: Reviewing a Glue crawler or job before production deployment, checking data-catalog encryption (EncryptionAtRest / ConnectionPasswordEncryption), validating JDBC connection SSL, auditing the execution role for pass-role or wildcard blast radius, inspecting a SecurityConfiguration for log / bookmark / spill encryption, flagging an EOL Glue version, or hardening ETL security posture across an account.
  activation_triggers: audit this Glue crawler, audit this Glue job, is my Glue catalog encrypted, check JDBC SSL on the Glue connection, Glue execution role too permissive, is the SecurityConfiguration set on the job, are Glue bookmarks encrypted, is the S3 source encrypted, harden Glue ETL, Glue 0.9 end of life
  invocation_schema: 'Input: either (a) a Glue crawler or job configuration (JSON / describe output) plus the DataCatalogEncryptionSettings, SecurityConfiguration, Connection, and IAM role policy documents, OR (b) a crawler / job name for live-account audit. Output: deterministic RESOURCE/VERDICT/REASON/ FINDINGS/REMEDIATION block per crawler or job, where VERDICT is in {NO_ENCRYPTION, OVERPERMISSIVE_ROLE, CONFIG_GAP, OK, ERROR}.'
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  keywords: Glue, crawler, Glue job, data catalog encryption, EncryptionAtRest, SecurityConfiguration, JDBC SSL, JDBC_ENFORCE_SSL, job bookmarks, S3 source encryption, execution role, PassRole, glue:CreateJob, glue:CreateCrawler, over-permissive role, Glue 0.9, EOL runtime, CloudWatch encryption, S3Encryptions, LakeFormation, ConnectionPasswordEncryption, ETL audit
  tags: glue, analytics, security, encryption, iam-role, jdbc, bookmarks, security-configuration, audit
---

# Glue Crawler & Job Auditor

## Mindset

**One-line takeaway:** the verdict is always the **worst** finding across all
dimensions, and three Glue concepts are routinely misjudged —
**`EncryptionAtRest` leaks catalog *metadata*, not processed data**,
**`SecurityConfiguration` does NOT encrypt the source** (it covers logs,
spills, and bookmarks), and **`glue:CreateJob` / `glue:CreateCrawler` are
silent pass-role vectors** just like `iam:PassRole`.

A Glue ETL pipeline has five independent security surfaces that operators
frequently conflate:

1. **Data Catalog encryption** (`EncryptionAtRest`, `ConnectionPasswordEncryption`)
   — two SEPARATE KMS-gated toggles. `EncryptionAtRest` encrypts catalog
   metadata (database / table / column names, partition values, schema JSON).
   `ConnectionPasswordEncryption` encrypts the JDBC password stored on the
   Connection object. Enabling one does NOT enable the other.
2. **SecurityConfiguration on the resource** — a named Glue resource that
   encrypts CloudWatch logs, S3 spill / temp writes, and job bookmarks. It
   does NOT encrypt the source data the job reads — that is the *source
   bucket's* own SSE setting.
3. **JDBC Connection transport** — `JDBC_ENFORCE_SSL` on the Connection's
   `ConnectionProperties`. Without it, Glue-to-DB traffic is cleartext.
4. **IAM execution role** — the role attached to the crawler / job. Its
   identity-based policy is the real blast radius; `glue:*` and `s3:*` on `*`
   are common and dangerous.
5. **Source S3 bucket encryption** — SSE-S3 or SSE-KMS on the bucket the
   crawler / job reads. This is the bucket's setting, not Glue's. Glue
   inherits; it does not control it.

## Quick reference — severity thresholds

| Condition | Verdict | Rule |
|---|---|---|
| `EncryptionAtRest.EncryptionMode: DISABLED` (catalog metadata in plaintext) | **NO_ENCRYPTION** | Step 1 |
| S3 source bucket with no SSE (no bucket-encryption config) | **NO_ENCRYPTION** | Step 2 |
| `SecurityConfiguration` missing AND `JobBookmarksEncryption` needed but absent | (no verdict alone — Step 4) | — |
| Role has admin wildcard (`Action: "*"` `Resource: "*"`) | **OVERPERMISSIVE_ROLE** | Step 3 |
| Role has `glue:*` / `s3:*` / `iam:PassRole` on `*` | **OVERPERMISSIVE_ROLE** | Step 3 |
| Role grants `glue:CreateJob` / `glue:CreateCrawler` on `*` + `iam:PassRole` on `*` | **OVERPERMISSIVE_ROLE** | Step 3 |
| JDBC Connection with `ConnectionType: JDBC` and no `JDBC_ENFORCE_SSL: true` | **CONFIG_GAP** | Step 4 |
| Job with no `SecurityConfiguration` (logs / spills / bookmarks unencrypted) | **CONFIG_GAP** | Step 4 |
| Job on Glue version `0.9` or `1.0` (EOL, no security patches) | **CONFIG_GAP** | Step 4 |
| `JobBookmarksEncryption.JobBookmarksEncryptionMode: DISABLED` on enabled bookmarks | **CONFIG_GAP** | Step 4 |
| All dimensions clean (catalog SSE-KMS, role least-privilege, SSL enforced, sec config present, Glue 2.0+, source encrypted) | **OK** | Step 5 |

See the ordered steps below for edge cases. The non-obvious Glue behaviors
that drive classification live in Step 0.

## Pre-flight: resource metadata gate (run before classification)

Before evaluating the configuration, classify the resource and its dependent
artifacts. Several attributes **short-circuit** the audit — misclassifying
them produces false positives that erode trust.

Live-account pre-flight commands moved to [references/diagnostic-commands.md](references/diagnostic-commands.md) — load on demand before a live audit.

| Attribute | Value | Effect on audit |
|---|---|---|
| Resource type | `Crawler` | Crawlers do not have a `GlueVersion`; skip the EOL check (Step 4d). Crawlers have `Targets` (S3Targets, JdbcTargets) instead of `Connections` on the job; map JdbcTargets to the JDBC Connection audit path. |
| Resource type | `Job` | Full audit including GlueVersion and SecurityConfiguration. |
| `EncryptionAtRest.EncryptionMode` | `DISABLED` | Catalog metadata is plaintext. Proceed to Step 1. |
| `EncryptionAtRest.EncryptionMode` | `SSE-KMS` | Catalog metadata is encrypted. OK for this dimension. |
| `ConnectionPasswordEncryption.ReturnConnectionPasswordEncrypted` | `false` | JDBC connection passwords are retrievable in plaintext. Treat as CONFIG_GAP (Step 4) even if `EncryptionAtRest` is SSE-KMS — they are independent. |
| `SecurityConfiguration` (on job) | absent / null | Logs, S3 spills, and bookmarks are unencrypted. CONFIG_GAP (Step 4b). |
| Named SecurityConfiguration | deleted / `EntityNotFoundException` | Same as absent — CONFIG_GAP. The job holds a dangling reference. |
| `GlueVersion` | `0.9`, `1.0` | **EOL.** No security patches. CONFIG_GAP (Step 4d). |
| `GlueVersion` | `2.0`, `3.0`, `4.0` | Supported. OK for this dimension. |
| LakeFormation governance | `TRUE` on target database | IAM `glue:*` permissions are NEUTRALIZED for LF-governed tables — the crawler / job needs BOTH IAM and LakeFormation grants. Note in REMEDIATION; do not downgrade the IAM verdict (a removed LF grant re-exposes IAM). |

**If the input config is malformed** (invalid JSON, missing `Role`, missing
`Targets` on a crawler), output:

```text
RESOURCE: <name>
VERDICT: ERROR
REASON: Glue configuration is malformed or missing required fields — cannot classify.
REMEDIATION: Re-fetch with `aws glue get-job --job-name <name>` or `aws glue get-crawler --name <name>` and re-audit.
```

## Process — Classification logic (apply in order, aggregate worst)

The verdict priority order is **NO_ENCRYPTION > OVERPERMISSIVE_ROLE >
CONFIG_GAP > OK**. NO_ENCRYPTION is the headline because it is a confirmed
current-state data / metadata exposure; OVERPERMISSIVE_ROLE is a potential
escalation path that requires an actor to exploit; CONFIG_GAP is a
configuration weakness that raises exposure but is not itself a breach.

### Step 0: Expert knowledge — non-obvious Glue behaviors that change classification

Each of these changes a verdict if ignored:

All 17 non-obvious-behaviour deep dives moved to [references/advanced-patterns.md](references/advanced-patterns.md) — load on demand before classifying edge findings.

### Step 1: Data Catalog EncryptionAtRest (highest priority — metadata exposure)

If `DataCatalogEncryptionSettings.EncryptionAtRest.EncryptionMode` is
`DISABLED` (or the field is absent, which Glue treats as DISABLED), the
catalog stores metadata in plaintext: database names, table names, column
names, partition values, and schema JSON. This is a metadata leak, not a
data leak — but column names frequently reveal PII attributes (`ssn`,
`email`, `date_of_birth`) and partition values can leak business structure.

- **EncryptionAtRest DISABLED** → **NO_ENCRYPTION**. This is the worst
  verdict because it is a confirmed current-state exposure of catalog
  metadata, including any sensitive column names.

- **EncryptionAtRest SSE-KMS (with or without a customer key)** → OK for
  this dimension. If `SseAwsKmsKeyId` is absent, Glue uses the
  AWS-managed `aws/glue` key — still encrypted, but note the key-ownership
  trade-off in REMEDIATION.

### Step 2: S3 source bucket encryption (data-at-rest on the source)

For each S3 target / source the crawler or job reads, check the bucket's
server-side encryption configuration (`aws s3api get-bucket-encryption`).

- **No bucket-encryption configuration (no SSE)** → **NO_ENCRYPTION**. The
  processed data is plaintext at rest on S3. This is independent of catalog
  encryption — a job can read an unencrypted bucket into an encrypted
  catalog (and vice versa).

- **SSE-S3 (AES256)** → OK for this dimension. SSE-S3 is the AWS default
  and provides at-rest encryption. Do NOT require SSE-KMS — SSE-S3 is a
  valid security posture for non-CMK-gated workloads.

- **SSE-KMS** → OK for this dimension. If a customer-managed CMK is used,
  note that the execution role needs `kms:Decrypt` on the key to read the
  source — otherwise the job fails at read time.

**Glue SecurityConfiguration does NOT cover the source.** Do NOT let a
present SecurityConfiguration on the job mask a Step 2 finding. The
SecurityConfiguration encrypts Glue's own writes (logs, spills, bookmarks),
not the source bucket.

### Step 3: IAM execution role blast radius

Classify the role's identity-based policy attached to the crawler / job
(`Role` field). The role is the real blast radius — Glue executes under it.

- **Admin wildcard** (`Action: "*"` `Resource: "*"`) → **OVERPERMISSIVE_ROLE**.
  Equivalent to `AdministratorAccess`.

- **Service wildcard on `*`** (`glue:*`, `s3:*`, or any privilege-escalation-
  service wildcard on `Resource: "*"`) → **OVERPERMISSIVE_ROLE**. `s3:*` on
  `*` grants read / write to every bucket in the account; `glue:*` on `*`
  grants catalog mutation including `glue:DeleteTable`.

- **`iam:PassRole` on `"*"`** → **OVERPERMISSIVE_ROLE**. Combined with
  `glue:CreateJob` / `glue:CreateCrawler` on `*` (Step 0), this is a
  privilege-escalation vector — the principal can attach any role to a new
  Glue resource and execute under it.

- **`NotAction` / `NotResource`** (inverse wildcards) → **OVERPERMISSIVE_ROLE**.
  These grant everything except the listed values; new Glue / S3 APIs are
  automatically included.

- **Named actions on specific resources** (e.g., `glue:BatchCreatePartition`
  on `arn:aws:glue:us-east-1:111:catalog` / `arn:aws:glue:...:database/prod`,
  `s3:GetObject` on `arn:aws:s3:::etl-source/*`) → least-privilege. OK for
  this dimension.

The role verdict is the worst statement (OVERPERMISSIVE_ROLE if any
statement is over-permissive). Apply the same logic as the
`iam-least-privilege-advisor` skill for the role policy.

### Step 4: Configuration gaps (no single gap is NO_ENCRYPTION, but each raises risk)

Each of these is CONFIG_GAP. They do not expose data directly but weaken the
security posture:

**4a. JDBC Connection SSL not enforced.** If the crawler / job references a
JDBC Connection (`ConnectionType: JDBC`) and the Connection's
`ConnectionProperties` does NOT include `JDBC_ENFORCE_SSL: "true"`, the
Glue-to-DB transport is cleartext. CONFIG_GAP. If `JDBC_ENFORCE_SSL: "true"`
is set but the DB uses a self-signed cert and no `JDBC_CUSTOM_CERT` /
`JDBC_CUSTOM_CERT_CHAIN` is configured, flag as CONFIG_GAP (CA trust gap).

**4b. SecurityConfiguration missing on job.** If the job has no
`SecurityConfiguration` field (or the named configuration was deleted),
CloudWatch logs, S3 spill / temp writes, and job bookmarks are all
unencrypted. CONFIG_GAP. For crawlers, this is less critical (crawlers
produce fewer spill writes) but logs and bookmarks still apply — flag
equally.

**4c. Job bookmarks unencrypted.** If the job has bookmarks enabled
(`JobBookmarksEncryption` present in the SecurityConfiguration but
`JobBookmarksEncryptionMode: DISABLED`), the bookmark state (source offsets,
processed partitions) is stored in plaintext. CONFIG_GAP. Bookmarks are
regional state — same job name in different regions has independent
bookmark state.

**4d. EOL Glue version.** If the job's `GlueVersion` is `0.9` or `1.0`,
the runtime is end-of-life with no security patches. CONFIG_GAP. Crawlers
do not have a `GlueVersion` — skip this check for crawler resources.

**4e. Connection password encryption disabled.** If
`ConnectionPasswordEncryption.ReturnConnectionPasswordEncrypted: false`,
JDBC connection passwords are retrievable in plaintext via
`glue:GetConnection`. CONFIG_GAP. This is independent of EncryptionAtRest
(Step 1).

### Step 5: Aggregation — worst finding wins

The final verdict is the **maximum severity** across all findings, where
NO_ENCRYPTION > OVERPERMISSIVE_ROLE > CONFIG_GAP > OK:

```text
verdict = max(catalog_encryption, s3_source_encryption, role_blast_radius, config_gap_findings)
```

If no findings (all dimensions OK), the verdict is **OK**.

## Output format (per resource)

```text
RESOURCE: <crawler-or-job-name>
VERDICT: NO_ENCRYPTION | OVERPERMISSIVE_ROLE | CONFIG_GAP | OK
REASON: <1-2 sentences citing the worst finding and its step number>
FINDINGS:
  - [NO_ENCRYPTION] <finding description (Step N)>
  - [CONFIG_GAP] <finding description (Step 4x)>
  - [OK] <dimension that passed>
REMEDIATION: <specific action per finding, or "None required" if OK>
```

### Worked example — catalog DISABLED + role wildcard

```text
RESOURCE: no-encryption-catalog-disabled
VERDICT: NO_ENCRYPTION
REASON: DataCatalogEncryptionSettings.EncryptionAtRest.EncryptionMode is
DISABLED (Step 1) — catalog metadata including column names is stored in
plaintext. The execution role also grants s3:* on * (Step 3).
FINDINGS:
  - [NO_ENCRYPTION] EncryptionAtRest.EncryptionMode is DISABLED — catalog metadata is plaintext (Step 1)
  - [OVERPERMISSIVE_ROLE] Execution role grants s3:* on Resource "*" (Step 3)
  - [OK] S3 source bucket has SSE-S3 enabled (Step 2)
REMEDIATION:
  1. Enable catalog encryption:
     aws glue put-data-catalog-encryption-settings \
       --data-catalog-encryption-settings EncryptionAtRest={EncryptionMode=SSE-KMS},ConnectionPasswordEncryption={ReturnConnectionPasswordEncrypted=true}
     NOTE: this is a breaking change — verify all catalog readers have kms:Decrypt on the catalog key first.
  2. Scope the role's s3:* to the specific source bucket ARN(s).
```

## Edge-case handling

Edge-case catalog (malformed config, crawler vs job, multi-source, cross-account, LF-governed) moved to [references/advanced-patterns.md](references/advanced-patterns.md) — load on demand.

## Anti-Patterns — NEVER

- NEVER treat `SecurityConfiguration` as source-data encryption. It encrypts
  CloudWatch logs, S3 spills / temps, and bookmarks — NOT the S3 source the
  job reads. A job with a perfect SecurityConfiguration can still read an
  unencrypted source. Audit the source bucket separately (Step 2).

- NEVER treat `EncryptionAtRest` and `ConnectionPasswordEncryption` as one
  setting. They are independent API fields with independent KMS keys.
  Enabling one and leaving the other disabled is a partial-config gap
  (CONFIG_GAP, Step 4e), not OK.

- NEVER flag `ConnectionPasswordEncryption` with no `AwsKmsKeyId` as a
  vulnerability. Glue falls back to the AWS-managed `aws/glue` key — the
  password is still encrypted-at-rest. Note the key-ownership trade-off but
  do NOT downgrade the verdict for this alone.

- NEVER treat SSE-S3 as insufficient. SSE-S3 (AES256) is a valid at-rest
  encryption posture. Requiring SSE-KMS for every bucket is a false
  positive. Only flag the ABSENCE of SSE (no bucket-encryption config) as
  NO_ENCRYPTION.

- NEVER overlook `glue:CreateJob` / `glue:CreateCrawler` as pass-role
  vectors. Combined with `iam:PassRole` on `"*"`, these let a principal
  execute under any role in the account — a direct privilege-escalation
  path, structurally identical to the `iam:PassRole` + EC2 / Lambda pattern.

- NEVER assume the named `SecurityConfiguration` exists. A job may
  reference a deleted configuration; Glue silently treats a missing
  reference as no encryption on logs / spills / bookmarks. Always
  `aws glue get-security-configuration --name <name>` and treat
  `EntityNotFoundException` as CONFIG_GAP.

- NEVER flag a crawler for a missing `GlueVersion`. Crawlers do not have a
  `GlueVersion` field — only jobs do. Flagging EOL version on a crawler is
  a false positive (Step 4d applies to jobs only).

- NEVER enable catalog encryption without verifying catalog readers have
  `kms:Decrypt` on the catalog key. Enabling `EncryptionAtRest: SSE-KMS` on
  a previously-DISABLED catalog is a breaking change — cross-account
  readers, Athena workgroups, and downstream ETL without the KMS grant
  silently break. Surface this in REMEDIATION as a migration step.

- NEVER treat `JDBC_ENFORCE_SSL: true` as sufficient alone for self-signed
  certificates. The Glue runtime must trust the DB's CA. For RDS the
  bundled CA suffices; for private-CA databases, `JDBC_CUSTOM_CERT` /
  `JDBC_CUSTOM_CERT_CHAIN` must be set. A connection with SSL enforced but
  an untrusted CA fails at runtime.

- NEVER evaluate `S3Encryptions` as a multi-layer array. Glue uses only the
  FIRST element. Multiple entries do not layer encryption — auditing
  `S3Encryptions[1+]` produces false confidence.

- NEVER downgrade the IAM role verdict when LakeFormation is enabled. LF
  neutralizes IAM for governed tables, but a removed LF grant re-exposes the
  IAM over-permission. The IAM policy is the classification truth; LF is a
  defense-in-depth layer, not a replacement.

- NEVER assume the Data Catalog encryption setting is global. It is
  regional. A multi-region pipeline must enable encryption in EACH region
  with `--region <r>`. A us-east-1 SSE-KMS setting does not propagate.

- NEVER treat `ConnectionPasswordEncryption: false` as a benign config gap.
  `glue:GetConnection` returns the JDBC password in plaintext in the API
  response when `ReturnConnectionPasswordEncrypted: false`. Any principal
  with `glue:GetConnection` on the connection ARN is one CLI call away from
  the live database password. Flag the role's `glue:GetConnection` grant as
  part of the blast-radius evaluation — the password is retrievable, not
  just stored.

- NEVER audit the catalog encryption setting without auditing the KMS key
  policy behind it. Unlike S3 (where a bucket policy can enforce a CMK),
  the Glue Data Catalog has NO resource-based policy — the catalog key's KMS
  policy is the ONLY access-control layer for cross-account readers. A
  cross-account reader returning `AccessDenied` after SSE-KMS enablement
  almost always has a key-policy gap, not an IAM gap.

- NEVER recommend deleting a Glue job or crawler as remediation without
  first confirming no downstream consumers (Athena views, QuickSight
  datasets, downstream ETL) depend on it. Catalog table drops cascade.

## Pre-flight safety checks (run before any remediation CLI)

- **MANDATORY CONFIRMATION GATE.** Before any state-changing operation
  (`UpdateJob`, `UpdateCrawler`, `PutDataCatalogEncryptionSettings`,
  `CreateSecurityConfiguration`, `DeleteCrawler`), the auditor MUST emit:
  `CONFIRM: About to <action> on <resource> in account <account>. This
  affects <consequence>. Proceed? (yes/no)` Do NOT execute the CLI command
  until the operator confirms.
- **Verify remediation permissions.** Before emitting `UpdateJob` /
  `UpdateCrawler` remediation, confirm the caller's role has
  `glue:UpdateJob` / `glue:UpdateCrawler`. Most read-only auditor roles
  CANNOT — the command will fail with `AccessDeniedException`.
- **Catalog encryption migration is a breaking change.** Before enabling
  `EncryptionAtRest: SSE-KMS` on a DISABLED catalog, enumerate every
  principal that reads the catalog (Athena workgroups, cross-account
  readers, downstream ETL) and verify each has `kms:Decrypt` on the
  catalog key. Enabling encryption without this coordination produces a
  silent multi-workload outage.
- **Capture current config for rollback.**
  `aws glue get-job --job-name <name> > /tmp/<name>-backup-$(date +%s).json`
  BEFORE any modification. Glue job / crawler configs are not versioned —
  there is no undo without a backup.
- **Bookmark encryption role check.** Before setting
  `JobBookmarksEncryptionMode: CSE-KMS`, verify the execution role has
  `kms:Decrypt` / `kms:GenerateDataKey` on the bookmark KMS key. A bookmark
  key the role cannot decrypt is an operational break (job fails at bookmark
  read).
- **Prefer additive changes.** Adding a SecurityConfiguration to a job is
  reversible; dropping a wildcard statement may break the workload.
  Sequence: (1) back up, (2) add the SecurityConfiguration, (3) verify the
  job runs, (4) only then tighten the role policy.

## Remediation guidance

Per-verdict remediation CLI (NO_ENCRYPTION, OVERPERMISSIVE_ROLE, CONFIG_GAP, OK) moved to [references/error-handling.md](references/error-handling.md) — load on demand when emitting REMEDIATION.

## Deep reference: Glue encryption layers

Encryption-layer deep reference (five surfaces, authorization layering, bookmark state semantics) moved to [references/advanced-patterns.md](references/advanced-patterns.md) — load on demand.

## Recent AWS features (2024-2026)

Recent feature notes moved to [references/advanced-patterns.md](references/advanced-patterns.md) — load on demand.

## References (load on demand)

- [references/advanced-patterns.md](references/advanced-patterns.md) — Step 0 expert-knowledge deep dives, edge-case catalog, Glue encryption-layer deep reference, recent AWS features.
- [references/error-handling.md](references/error-handling.md) — remediation CLI per verdict (NO_ENCRYPTION, OVERPERMISSIVE_ROLE, CONFIG_GAP, OK) with breaking-change and rollback notes.
- [references/diagnostic-commands.md](references/diagnostic-commands.md) — live-account pre-flight checks (permissions, SecurityConfiguration existence, connection password encryption).

## Domain

AWS CloudOps / Glue Analytics Security & Compliance.

## AWS documentation

- **AWS Glue Developer Guide** — https://docs.aws.amazon.com/glue/latest/dg/what-is-glue.html
- **Glue Security** — https://docs.aws.amazon.com/glue/latest/dg/security.html
- **Glue API Reference** — https://docs.aws.amazon.com/glue/latest/dg/aws-glue-api.html
- **Glue CLI Reference** — https://docs.aws.amazon.com/cli/latest/reference/glue/
- **Glue Data Quality** — https://docs.aws.amazon.com/glue/latest/dg/data-quality.html
