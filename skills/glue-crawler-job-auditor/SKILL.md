---
name: glue-crawler-job-auditor
description: >-
  Audits AWS Glue crawlers and jobs (plus their data-catalog encryption, JDBC
  connections, IAM execution roles, security configurations, job bookmarks,
  and S3 source encryption) for data-at-rest exposure, over-permissive
  pass-role blast radius, and configuration gaps. Emits a deterministic
  verdict — NO_ENCRYPTION | OVERPERMISSIVE_ROLE | CONFIG_GAP | OK — per
  crawler or job with enumerated findings and CLI remediation. Use when
  reviewing Glue crawlers/jobs before production, checking catalog encryption,
  validating JDBC SSL, tightening the execution role, or hardening ETL
  security posture.
version: 0.1.0
author: Jacky Chan — AWS Community Builder
license: Apache-2.0
compatibility: >-
  Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex,
  Gemini). No AWS CLI required for offline config classification. Live-account
  audits use aws glue get-data-catalog-encryption-settings, get-security-
  configuration, get-job, get-crawler, get-connection, and aws s3api
  get-bucket-encryption (AWS CLI v2, SSO or key-based credentials).
keywords:
  - Glue
  - crawler
  - Glue job
  - data catalog encryption
  - EncryptionAtRest
  - SecurityConfiguration
  - JDBC SSL
  - JDBC_ENFORCE_SSL
  - job bookmarks
  - S3 source encryption
  - execution role
  - PassRole
  - glue:CreateJob
  - glue:CreateCrawler
  - over-permissive role
  - Glue 0.9
  - EOL runtime
  - CloudWatch encryption
  - S3Encryptions
  - LakeFormation
  - ConnectionPasswordEncryption
  - ETL audit
tags: [glue, analytics, security, encryption, iam-role, jdbc, bookmarks, security-configuration, audit]
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: true
  phase: 2
  supports_pipeline: true
  entry_point: false
  family: Analytics
  verdict_shape: "NO_ENCRYPTION | OVERPERMISSIVE_ROLE | CONFIG_GAP | OK"
  when_to_use: >-
    Reviewing a Glue crawler or job before production deployment, checking
    data-catalog encryption (EncryptionAtRest / ConnectionPasswordEncryption),
    validating JDBC connection SSL, auditing the execution role for pass-role
    or wildcard blast radius, inspecting a SecurityConfiguration for log /
    bookmark / spill encryption, flagging an EOL Glue version, or hardening
    ETL security posture across an account.
  activation_triggers:
    - "audit this Glue crawler"
    - "audit this Glue job"
    - "is my Glue catalog encrypted"
    - "check JDBC SSL on the Glue connection"
    - "Glue execution role too permissive"
    - "is the SecurityConfiguration set on the job"
    - "are Glue bookmarks encrypted"
    - "is the S3 source encrypted"
    - "harden Glue ETL"
    - "Glue 0.9 end of life"
  invocation_schema: >-
    Input: either (a) a Glue crawler or job configuration (JSON / describe
    output) plus the DataCatalogEncryptionSettings, SecurityConfiguration,
    Connection, and IAM role policy documents, OR (b) a crawler / job name
    for live-account audit. Output: deterministic RESOURCE/VERDICT/REASON/
    FINDINGS/REMEDIATION block per crawler or job, where VERDICT is in
    {NO_ENCRYPTION, OVERPERMISSIVE_ROLE, CONFIG_GAP, OK, ERROR}.
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

**Live-account pre-flight checks (skip if doing offline config audit):**
1. Verify the caller can run `glue:GetJob` / `glue:GetCrawler` — most
   read-only auditor roles can, but remediation (`UpdateJob`,
   `UpdateCrawler`) usually requires elevated grants. Surface this BEFORE
   the operator approves a change.
2. Confirm the named `SecurityConfiguration` actually EXISTS. A job may
   reference `SecurityConfiguration: prod-sec-config` that was deleted; Glue
   silently treats a missing reference as no encryption on logs / spills /
   bookmarks. Run `aws glue get-security-configuration --name <name>` and
   treat a `EntityNotFoundException` as CONFIG_GAP (Step 4), not OK.
3. For JDBC connections, fetch the connection password encryption setting
   AND the IAM role policy in the same pass — the connection password is
   only meaningful if `ConnectionPasswordEncryption.ReturnConnectionPasswordEncrypted`
   is true; otherwise the password is retrievable in plaintext via
   `glue:GetConnection`.

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

- **`SecurityConfiguration` does NOT encrypt the source.** It encrypts
  CloudWatch logs (`CloudWatchEncryption`), S3 spill / temp / audit-write
  output (`S3Encryptions`), and job bookmarks (`JobBookmarksEncryption`).
  The source S3 bucket encryption is the BUCKET's setting, fetched via
  `aws s3api get-bucket-encryption`. A job with a perfect SecurityConfiguration
  can still read an unencrypted source — flag the source separately (Step 2).
  Do NOT let a present SecurityConfiguration mask a Step 2 finding.

- **`EncryptionAtRest` and `ConnectionPasswordEncryption` are INDEPENDENT.**
  `EncryptionAtRest` covers catalog metadata (table / column / partition).
  `ConnectionPasswordEncryption` covers the JDBC password on Connection
  objects. The Glue console groups them under "Catalog encryption" but they
  are separate API fields and separate KMS keys. Enabling one and leaving
  the other disabled is a common partial-config gap.

- **`ConnectionPasswordEncryption` with no `AwsKmsKeyId` uses the
  AWS-managed `aws/glue` key.** This is an AWS-managed CMK, not a
  customer-managed key. It is still encrypted-at-rest, but the key policy is
  not customer-editable and CloudTrail attribution is coarser. Note in
  REMEDIATION; do NOT downgrade the verdict for this alone.

- **`glue:CreateJob` / `glue:CreateCrawler` are pass-role vectors.** Like
  `iam:PassRole`, these accept a `Role` ARN and execute under that role's
  permissions. A principal with `glue:CreateJob` on `*` and `iam:PassRole`
  on `*` can spin up a job that runs under any role in the account — a
  direct privilege-escalation path. Treat the combination as OVERPERMISSIVE_ROLE.

- **Job bookmark encryption requires `kms:Decrypt` in the role.** If
  `JobBookmarksEncryption.JobBookmarksEncryptionMode: CSE-KMS` is set but
  the execution role lacks `kms:Decrypt` on the bookmark KMS key, the job
  FAILS at bookmark read — an operational break, not a security finding.
  Note in REMEDIATION as a coordination requirement, not a verdict driver.

- **`S3Encryptions` is an array but only the FIRST element is used.** Glue
  accepts an array of S3 encryption settings, but applies only the first
  entry to spill / temp writes. Multiple entries do NOT layer. When
  auditing, evaluate `S3Encryptions[0]` only.

- **Catalog encryption change is a breaking change.** Enabling
  `EncryptionAtRest: SSE-KMS` on a previously-DISABLED catalog breaks every
  principal that lacks `kms:Decrypt` on the catalog key — this includes
  cross-account readers, Athena workgroups, and downstream ETL. Surface this
  in REMEDIATION as a migration step, not a one-liner.

- **JDBC SSL alone is insufficient for self-signed certs.** `JDBC_ENFORCE_SSL: true`
  forces TLS, but the Glue runtime must TRUST the DB's certificate authority.
  For Amazon RDS, the bundled RDS root CA is trusted. For self-signed or
  private-CA databases, the CA cert must be uploaded via the Connection's
  `JDBC_CUSTOM_CERT` / `JDBC_CUSTOM_CERT_CHAIN` properties. A connection
  with `JDBC_ENFORCE_SSL: true` and an untrusted CA fails at runtime —
  classify as CONFIG_GAP, not OK, and note the CA requirement.

- **Crawler role least-privilege write path is `glue:BatchCreatePartition`
  + `glue:CreateTable` + `glue:UpdateDatabase` on specific catalog resources,
  NOT `glue:*`.** Over-granting as `glue:Create*` or `glue:*` on `*` is the
  most common crawler-role mistake. The read path needs `glue:GetTable`,
  `glue:GetDatabase`, `glue:GetTables`, `glue:GetDatabases`.

- **LakeFormation neutralizes IAM for governed tables.** If the target
  catalog database is LF-governed, IAM `glue:*` permissions are ignored for
  LF-authorized operations — the crawler needs `lakeformation:GrantPermissions`
  or a named LF service role. The IAM role verdict still stands (a removed
  LF grant re-exposes IAM), but note the LF dependency in REMEDIATION.

- **Data Catalog is REGIONAL.** Encryption settings are per-region. A
  multi-region pipeline must enable catalog encryption in EACH region
  independently — a us-east-1 SSE-KMS setting does not propagate to
  eu-west-1. When auditing a multi-region pipeline, fetch settings per
  region with `--region <r>`.

- **`GlueVersion` 0.9 and 1.0 are end-of-life.** They run unsupported Spark
  runtimes with no security patches. Glue 2.0 (Spark 2.4) is the minimum
  supported line; Glue 3.0 (Spark 3.1) and Glue 4.0 (Spark 3.3/3.5) are
  current. EOL runtimes are CONFIG_GAP.

- **`glue:UpdateCrawler` / `glue:UpdateJob` are remediation-grade actions.**
  A read-only auditor role typically CANNOT run them. Before emitting
  remediation CLI, verify the caller's identity-based policy includes these
  actions; otherwise the command fails with `AccessDeniedException`.

- **`glue:GetConnection` returns the JDBC PASSWORD in plaintext when
  `ReturnConnectionPasswordEncrypted: false`.** This is not just a config
  gap — it is a direct credential-exfiltration path. Any principal with
  `glue:GetConnection` on the connection ARN can retrieve the live database
  password from the API response's `ConnectionProperties.PASSWORD` field via
  a single CLI call (`aws glue get-connection --name <conn>`). Treat a
  Connection with `ReturnConnectionPasswordEncrypted: false` as a
  CONFIG_GAP **and** flag the role's `glue:GetConnection` grant as part of
  the blast-radius evaluation — the password is one API call away.

- **`glue:BatchGetJobs` / `glue:BatchGetCrawlers` enumerate role ARNs.**
  These read-only actions return the full config including the `Role` field
  for every job / crawler. A principal with `glue:BatchGetJobs` can harvest
  every execution-role ARN in the account, then target those roles via
  `glue:CreateJob` + `iam:PassRole`. This is the enumeration half of the
  pass-role escalation chain — flag `glue:BatchGet*` on `*` alongside
  `glue:Create*` + `iam:PassRole` as a compound escalation vector.

- **`JobBookmarksEncryption` CSE-KMS is CLIENT-SIDE, not server-side.** The
  `CSE-` prefix means the Glue SDK encrypts the bookmark state with the KMS
  key on the client (the job's execution container) BEFORE transmitting it to
  the Glue service. The bookmark state is never sent in plaintext over the
  wire. This is subtly different from `SSE-KMS` (server-side). The practical
  consequence: the execution role needs BOTH `kms:GenerateDataKey` (to
  encrypt new bookmark state) AND `kms:Decrypt` (to read prior state), and a
  key-policy change that revokes one silently half-breaks bookmarking
  (writes succeed, reads fail — the job appears to make progress but loses
  state on retry).

- **Catalog SSE-KMS cross-account key-policy trap.** Unlike S3 (where a
  bucket policy can enforce a CMK), the Glue Data Catalog has NO
  resource-based policy. The KMS key policy behind `EncryptionAtRest: SSE-KMS`
  is the ONLY access-control layer beyond IAM for cross-account catalog
  reads. Enabling SSE-KMS on a catalog shared via Resource Link to account
  222222222222 requires the catalog key's policy to grant
  `kms:Decrypt` to `arn:aws:iam::222222222222:root` (or the specific reader
  role). A catalog that silently returns `AccessDenied` to cross-account
  readers after encryption enablement almost always has a key-policy gap, not
  an IAM gap. Always audit the catalog key policy alongside the catalog
  encryption setting.

- **Crawler schema-inference sampling threshold.** A crawler infers schema
  by sampling the first file(s) at each S3 target prefix — the default is
  one file per leaf folder. This means a crawler on a 10 TB source reads <
  1 MB to determine the table schema. If the first file has a different
  column set from the rest (e.g., a schema-drift header file), the catalog
  gets the WRONG schema silently — every downstream Athena query against that
  table returns NULLs for the missing columns. This is an integrity risk,
  not a security verdict driver, but note it when the crawler targets a
  schema-on-read source (JSON / CSV) without a classifier.

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

- **Partially malformed config.** If the config JSON parses but individual
  sections are missing (no `Role`, no `Targets` on a crawler, no
  `ConnectionProperties` on a JDBC connection), classify each present
  section normally and emit an ERROR note for each missing section: "Role
  field absent — cannot audit IAM blast radius (Step 3 skipped)." Do NOT
  silently classify the entire resource as ERROR when only one dimension is
  broken.

- **Crawler vs Job.** Crawlers do not have `GlueVersion` or `SecurityConfiguration`
  in the same way jobs do — a crawler's security config is set via the
  `CrawlerSecurityConfiguration` field (Glue API). Map `CrawlerSecurityConfiguration`
  to the Step 4b audit path. Skip Step 4d (EOL version) for crawlers.

- **Multiple S3 sources.** A job or crawler may read from multiple S3 paths.
  Evaluate each source bucket independently. If ANY source is unencrypted,
  the Step 2 verdict is NO_ENCRYPTION — one unencrypted source exposes that
  data even if others are encrypted.

- **Cross-account catalog access.** If the catalog is shared via Resource
  Link or cross-account `glue:GrantPermissions`, the catalog encryption key
  policy must permit the cross-account principal to `kms:Decrypt`. A catalog
  with SSE-KMS and a key policy that does not include the external account
  silently breaks cross-account reads. Note in REMEDIATION as a key-policy
  coordination step.

- **Connection with `ConnectionType: S3` (not JDBC).** S3-type connections
  do not have `JDBC_ENFORCE_SSL`. Skip Step 4a for non-JDBC connections.

- **Job with no bookmarks.** If `JobBookmarksEncryption` is DISABLED but the
  job does not use bookmarks (e.g., a full-reload job that always reprocesses),
  the bookmark finding is informational, not a CONFIG_GAP verdict driver.
  Note it but do not let it force CONFIG_GAP if all other dimensions are OK.

- **LakeFormation-governed catalog.** If the target database is LF-governed,
  IAM `glue:*` permissions are neutralized for LF-authorized operations.
  Note the LF dependency but do NOT downgrade the IAM role verdict — a
  removed LF grant re-exposes the IAM over-permission.

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

### For NO_ENCRYPTION — catalog EncryptionAtRest DISABLED (Step 1)

1. **Before enabling**, enumerate catalog readers and verify each has
   `kms:Decrypt` on the catalog key (or grant it). This is a breaking change.
2. Enable catalog encryption:
   ```bash
   aws glue put-data-catalog-encryption-settings \
     --region <r> \
     --data-catalog-encryption-settings \
       EncryptionAtRest={EncryptionMode=SSE-KMS,SseAwsKmsKeyId=alias/glue-catalog},\
       ConnectionPasswordEncryption={ReturnConnectionPasswordEncrypted=true,AwsKmsKeyId=alias/glue-catalog}
   ```
3. Verify: `aws glue get-data-catalog-encryption-settings --region <r>`.
4. If using a customer-managed CMK, ensure the key policy grants
   `kms:Decrypt` to every catalog reader principal.

### For NO_ENCRYPTION — S3 source unencrypted (Step 2)

1. Enable SSE on the source bucket:
   ```bash
   aws s3api put-bucket-encryption \
     --bucket <source-bucket> \
     --server-side-encryption-configuration \
       '{"Rules":[{"ApplyServerSideEncryptionByDefault":{"SSEAlgorithm":"AES256"}}]}'
   ```
2. For SSE-KMS, add the KMS key ARN and ensure the execution role has
   `kms:Decrypt` on the key.
3. Existing objects are NOT retroactively encrypted by bucket-default
   changes. Use S3 Batch Operations or a Copy job to encrypt existing data.

### For OVERPERMISSIVE_ROLE (Step 3)

1. Derive a least-privilege policy from CloudTrail `glue:*` and `s3:*`
   events for the role over the last 90 days.
2. Replace `glue:*` with named actions (`glue:BatchCreatePartition`,
   `glue:GetTable`, `glue:GetDatabase`, `glue:UpdateTable`, etc.) scoped to
   the specific catalog / database / table ARNs.
3. Replace `s3:*` on `*` with `s3:GetObject` / `s3:ListBucket` on the
   specific source bucket ARN(s) and `s3:PutObject` on the spill / output
   bucket ARN(s).
4. Restrict `iam:PassRole` to the specific Glue service-role ARN the
   workload needs, and add `iam:PassedToService: glue.amazonaws.com` as a
   condition.
5. Convert `NotAction` / `NotResource` to explicit `Action` / `Resource`
   allow-lists.

### For CONFIG_GAP — JDBC SSL (Step 4a)

1. Update the connection to enforce SSL:
   ```bash
   aws glue update-connection \
     --connection-name <conn> \
     --connection-input '{
       "ConnectionType":"JDBC",
       "ConnectionProperties":{"JDBC_CONNECTION_URL":"...","JDBC_ENFORCE_SSL":"true","USERNAME":"..."},
       "PhysicalConnectionRequirements":{...}
     }'
   ```
2. For self-signed / private-CA databases, add `JDBC_CUSTOM_CERT` /
   `JDBC_CUSTOM_CERT_CHAIN` pointing to the uploaded CA cert in S3.

### For CONFIG_GAP — SecurityConfiguration missing (Step 4b)

1. Create a SecurityConfiguration:
   ```bash
   aws glue create-security-configuration \
     --name prod-glue-sec \
     --encryption-configuration '{
       "CloudWatchEncryption":{"CloudWatchEncryptionMode":"SSE-KMS"},
       "S3Encryptions":[{"EncryptionMode":"SSE-KMS"}],
       "JobBookmarksEncryption":{"JobBookmarksEncryptionMode":"CSE-KMS"}
     }'
   ```
2. Attach it to the job:
   ```bash
   aws glue update-job --job-name <name> --job-update '{"SecurityConfiguration":"prod-glue-sec"}'
   ```
3. For crawlers, set `CrawlerSecurityConfiguration` via `update-crawler`.

### For CONFIG_GAP — EOL Glue version (Step 4d)

1. Upgrade the job to Glue 4.0:
   ```bash
   aws glue update-job --job-name <name> \
     --job-update '{"GlueVersion":"4.0","Command":{"Name":"glueetl","ScriptLocation":"...","PythonVersion":"3"}}'
   ```
2. Test the job — Spark version changes (2.4 → 3.3) may require script
   adjustments (DataFrame API, partitioning behavior).

### For CONFIG_GAP — Connection password encryption disabled (Step 4e)

1. Enable it as part of the catalog encryption settings (see Step 1
   remediation — `ConnectionPasswordEncryption` is set in the same
   `PutDataCatalogEncryptionSettings` call as `EncryptionAtRest`).
2. Existing connections' passwords are re-encrypted on next read; no
   migration action is required for the passwords themselves.

### For OK

1. No remediation required for the current posture.
2. Recommend periodic re-audit — SecurityConfigurations can be deleted,
   catalog encryption can be disabled by a later change, and the role
   policy can drift.
3. For multi-region pipelines, verify the same posture in every region:
   ```bash
   for r in us-east-1 eu-west-1 ap-southeast-1; do
     echo "=== $r ==="
     aws glue get-data-catalog-encryption-settings --region $r
   done
   ```
   A us-east-1 SSE-KMS setting does NOT propagate — each region's catalog
   encryption is independent.

## Deep reference: Glue encryption layers

### The five independent encryption surfaces

| Surface | What it protects | API field | Who controls it |
|---|---|---|---|
| `EncryptionAtRest` | Catalog metadata (table / column / partition names, schema JSON) | `DataCatalogEncryptionSettings.EncryptionAtRest` | Account-level Glue setting |
| `ConnectionPasswordEncryption` | JDBC password stored on Connection objects | `DataCatalogEncryptionSettings.ConnectionPasswordEncryption` | Account-level Glue setting |
| `SecurityConfiguration.CloudWatchEncryption` | CloudWatch log groups emitted by the job | `EncryptionConfiguration.CloudWatchEncryption` | Per-job / per-crawler |
| `SecurityConfiguration.S3Encryptions` | S3 spill / temp / audit-write output | `EncryptionConfiguration.S3Encryptions[0]` | Per-job / per-crawler |
| `SecurityConfiguration.JobBookmarksEncryption` | Bookmark state (source offsets, processed partitions) | `EncryptionConfiguration.JobBookmarksEncryption` | Per-job |
| S3 source bucket SSE | Source data at rest on S3 | Bucket's own `server-side-encryption-configuration` | Bucket owner (NOT Glue) |

### Authorization layering (catalog access)

Glue catalog access is evaluated in this order:

1. **Organizations SCP** — sets the maximum permissions for the account.
2. **Resource-based policy** — Glue resource-based policies are rare; the
   catalog itself does not have a resource-based policy (unlike S3 / KMS).
3. **LakeFormation grant** (if LF governs the database / table) — LF grants
   are evaluated BEFORE IAM for governed resources. A principal with no LF
   grant is denied regardless of IAM.
4. **IAM identity-based policy** — the execution role's policy. This is the
   classification truth for Step 3.
5. **KMS key policy** (if EncryptionAtRest is SSE-KMS) — the caller must
   have `kms:Decrypt` on the catalog key to read encrypted metadata. This
   is a separate gate from IAM / LF.

### Bookmark state semantics

Bookmarks store the processed state of a source (S3 object versions, JDBC
offsets, DynamoDB scan positions). They are **regional** — the same job
name in us-east-1 and eu-west-1 has independent bookmark state. Bookmark
encryption (`CSE-KMS`) encrypts this state at rest using client-side
encryption before it is stored in the Glue internal state store. A job with
`CSE-KMS` bookmarks that loses `kms:Decrypt` on the bookmark key fails at
bookmark read — an operational break, not a security finding.

## Domain

AWS CloudOps / Glue Analytics Security & Compliance.
