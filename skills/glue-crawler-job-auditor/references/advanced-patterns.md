# Advanced Patterns — Glue Crawler & Job Auditor

Expert-knowledge deep dives, edge-case catalog, and encryption-layer reference moved verbatim from SKILL.md (progressive disclosure — load on demand).

## Step 0: Expert knowledge — non-obvious Glue behaviors that change classification

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

## Recent AWS features (2024-2026)

- **Glue 5.0 (Spark 3.5, Python 3.11) (2024-2025):** Glue now supports Spark 3.5 and Python 3.11 with Glue version 5.0. Auditors should verify that jobs are upgraded from Glue 3.0/4.0 — older versions may have unpatched vulnerabilities in their runtime.
- **Glue Flex execution class (2024):** Glue Flex uses spare compute capacity at a lower cost. Auditors should verify whether production jobs use Flex (which can be interrupted) vs Standard execution — Flex is appropriate for batch/non-critical jobs only.
- **Glue Data Quality GA (2024):** Glue Data Quality enables automated data quality rules on catalog tables. Auditors should verify that data quality rules are configured for regulated datasets and that rule evaluation failures trigger alerts.
- **Cross-account catalog sharing improvements (2024):** Enhanced Lake Formation cross-account catalog sharing. Auditors should verify that Glue crawlers accessing cross-account catalogs have appropriate Lake Formation grants.

