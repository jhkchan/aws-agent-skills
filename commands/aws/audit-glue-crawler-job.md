---
description: Audit an AWS Glue crawler or job for data-catalog encryption, JDBC connection SSL, IAM execution-role blast radius, SecurityConfiguration coverage (logs / spills / bookmarks), job-bookmark encryption, EOL Glue version, and S3 source encryption.
nl_triggers:
  - "audit this Glue crawler"
  - "audit this Glue job"
  - "is my Glue catalog encrypted"
  - "Glue JDBC SSL check"
  - "Glue execution role too permissive"
  - "Glue SecurityConfiguration missing"
  - "are Glue bookmarks encrypted"
  - "is the Glue S3 source encrypted"
  - "harden Glue ETL"
  - "Glue 0.9 end of life"
  - "Glue crawler security"
  - "Glue job pass role"
  - "EncryptionAtRest disabled"
routes_to: glue-crawler-job-auditor
---

# /aws:audit-glue-crawler-job

Activate the `glue-crawler-job-auditor` skill and audit one or more AWS Glue
crawler or job configurations for security exposure.

## What it does

Reads a Glue crawler / job config (Role, GlueVersion, SecurityConfiguration,
Connections, Targets) plus the DataCatalogEncryptionSettings,
SecurityConfiguration resource, JDBC Connection properties, S3 source bucket
encryption, and the execution-role identity-based policy, then applies the
ordered classification logic:

1. Data Catalog EncryptionAtRest — DISABLED leaks catalog metadata (table,
   column, partition names) in plaintext — NO_ENCRYPTION.
2. S3 source bucket encryption — no SSE means processed data is plaintext
   at rest — NO_ENCRYPTION (independent of catalog encryption).
3. IAM execution role blast radius — admin wildcard, `glue:*` / `s3:*` on
   `*`, `iam:PassRole` on `*` (with `glue:CreateJob`/`CreateCrawler` as
   pass-role vectors) — OVERPERMISSIVE_ROLE.
4. Configuration gaps — JDBC `JDBC_ENFORCE_SSL` not enforced, missing /
   deleted SecurityConfiguration, `JobBookmarksEncryption` DISABLED,
   `GlueVersion` 0.9 / 1.0 (EOL), `ConnectionPasswordEncryption` disabled —
   CONFIG_GAP.
5. Aggregation — worst finding wins (NO_ENCRYPTION > OVERPERMISSIVE_ROLE >
   CONFIG_GAP > OK).

Emits a deterministic VERDICT per resource:

```text
RESOURCE: <crawler-or-job-name>
VERDICT: NO_ENCRYPTION | OVERPERMISSIVE_ROLE | CONFIG_GAP | OK
REASON: <1-2 sentences citing the worst finding and step number>
FINDINGS:
  - [NO_ENCRYPTION] <finding description (Step N)>
  - [CONFIG_GAP] <finding description (Step 4x)>
REMEDIATION: <specific action per finding, or "None required" if OK>
```

## When to invoke

Paste a Glue crawler / job configuration (with DataCatalogEncryptionSettings,
SecurityConfiguration, Connection, and role policy) and ask any of:

- "audit this Glue job"
- "is my Glue catalog encrypted?"
- "is the JDBC connection using SSL?"
- "is the execution role too permissive?"
- "does the job have a security configuration?"
- "are the Glue bookmarks encrypted?"
- "is the Glue 0.9 runtime end of life?"

A bare job or crawler name plus any audit verb also routes here via the
orchestrator.

## Inputs

- A Glue job or crawler configuration (JSON / describe output), pasted inline
  or referenced by file path.
- DataCatalogEncryptionSettings (EncryptionAtRest, ConnectionPasswordEncryption).
- The named SecurityConfiguration resource (CloudWatchEncryption,
  S3Encryptions, JobBookmarksEncryption) if one is attached.
- JDBC Connection properties (ConnectionType, ConnectionProperties) if the
  job reads from a database.
- The S3 source bucket server-side-encryption configuration.
- The execution role's identity-based policy document (JSON).
- For multi-region pipelines: provide per-region catalog encryption settings.

## Outputs

- One VERDICT block per resource (multiple findings aggregate to the worst
  verdict).
- Enumerated FINDINGS list with per-finding severity and step citation.
- Specific remediation: enable catalog encryption (with KMS-grant migration),
  scope the role, enforce JDBC SSL, attach a SecurityConfiguration, upgrade
  Glue version, encrypt bookmarks.

## Related

- `/aws:pipeline` to enter the full CloudOps pipeline (this skill is the
  Phase 2 Audit specialist for Glue analytics security).
- `/aws:audit-iam-least-privilege` for deeper IAM policy analysis of the
  Glue execution role.
- `/aws:audit-kms-key-policy` for the KMS key policy behind catalog / bookmark
  encryption.
