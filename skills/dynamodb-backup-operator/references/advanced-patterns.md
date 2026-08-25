# Advanced Patterns (load on demand) — DynamoDB Backup Restore Operator

Step-0 expert knowledge, cost heuristics, edge cases, and 2024-2026 feature changes, moved verbatim from SKILL.md.


---

## Cost/time baselines (2026) (moved from SKILL.md)


- On-demand backup create time: minutes for small tables, scaling with
  table size (DynamoDB service-managed, stored within DynamoDB — NOT S3).
- Restore time: proportional to source data size; the new table is not
  ACTIVE until restore completes (status transitions RESTORING → ACTIVE).
- PITR cost: ~$0.20/GB-month for continuous-backup storage + ~$0.10/GB
  for restore data read.
- On-demand backup storage: ~$0.10/GB-month (DynamoDB service-managed).
- Export to S3: ~$0.008/GB read from DynamoDB + S3 storage of the
  exported Parquet/JSON; import from S3: ~$0.008/GB write to the new
  table + S3 GET cost.

## Step 0: Expert knowledge — non-obvious DynamoDB backup/restore behaviors (moved from SKILL.md)


- **PITR restore recovers to any second in the 35-day window, not just
  snapshot instants.** `restore-table-to-point-in-time
  --restore-date-time <ts>` accepts any timestamp within
  `[EarliestRestorableDateTime, LatestRestorableDateTime]` with
  second-level precision. `LatestRestorableDateTime` typically lags
  real-time by a few seconds (NOT 5 minutes like RDS). On-demand
  snapshots are only needed for longer-term retention beyond 35 days.

- **Restore creates a NEW table with a NEW name.** Always. The source
  table is untouched. Operators must update application connection
  strings, IAM resource policies, CloudWatch alarms, and DNS aliases
  to point at the new table name. This is the single most common
  DynamoDB restore surprise.

- **Restore does NOT copy: autoscaling, alarms, IAM resource policies,
  Streams, TTL, tags.** The restored table inherits schema, GSI/LSI
  definitions, billing mode, and provisioned throughput from the
  snapshot/PITR source — but everything else must be reconfigured
  manually. Plan a post-restore checklist.

- **On-demand backups are stored within DynamoDB service, NOT S3.**
  `create-backup` produces a backup ARN stored and managed by DynamoDB
  (~$0.10/GB-month). For S3-based backup (analytics, cross-region,
  longer retention), use `export-table-to-point-in-time` (exports to
  S3 in Parquet/DynamoDB JSON) — that is a different feature with a
  different cost model.

- **PITR cost is charged on the change volume, not the table size.**
  DynamoDB bills PITR storage based on the bytes modified during the
  35-day window. A read-heavy table with low write volume costs very
  little in PITR. A write-heavy table can approach ~2x the data size
  in PITR storage over 35 days.

- **`restore-table-to-point-in-time` supports selective restore.** The
  optional `--sse-specification-override`, `--billing-mode-override`,
  and the new (2024-2025) selective-restore projection filter (project
  specific attributes) let you build a smaller restored table. Use
  this for partial recovery (e.g., only one partition key range).

- **Restore does NOT copy the table class.** A source table on
  `STANDARD_INFREQUENT_ACCESS` restores to `STANDARD` by default. Set
  `--table-class-override STANDARD_INFREQUENT_ACCESS` explicitly.

- **On-demand backup retention is unlimited but billed.** On-demand
  backups (created via `create-backup`) do NOT auto-expire — they
  persist until explicitly deleted via `delete-backup`. Set a
  retention reminder (tags or AWS Backup plan) to avoid perpetual
  billing.

- **Cross-region restore via AWS Backup.** AWS Backup vaults support
  cross-region copy and cross-account restore for DynamoDB. The
  source backup must be in an AWS Backup vault (not just a
  DynamoDB-managed on-demand backup). Use
  `aws backup start-restore-job` with the recovery-point ARN.

- **Cross-region restore via S3 export/import.** For tables NOT in an
  AWS Backup vault, the cross-region path is: `export-table-to-point-
  in-time` in source region → S3 bucket (with cross-region replication
  or a copy step) → `import-table` in target region. The import
  creates a new table from the S3 data.

- **GSI/LSI are recreated on restore, but their data must rebuild.**
  The restored table's GSI/LSI definitions are copied from the source,
  but the index data is rebuilt as the base-table data streams in.
  GSIs are not queryable until the rebuild completes — monitor
  `IndexStatus` transitioning to `ACTIVE`.

- **`restore-table-from-backup` with a backup ARN is the snapshot-
  style restore.** `restore-table-to-point-in-time` uses the
  continuous backup (PITR) — different code path, different CLI.
  Choose by what recovery point you need (a snapshot instant vs any
  second in the window).

- **`DeletionProtectionEnabled` on the source does NOT block restore.**
  Restore creates a new table — the source's deletion protection is
  irrelevant. However, the new table does NOT inherit
  `DeletionProtectionEnabled`; enable it post-restore if needed.

- **`export-table-to-point-in-time` requires PITR enabled on the
  source.** Even though the export target is S3, the export reads from
  the continuous-backup store. A table with `PITRStatus: DISABLED`
  cannot export.

- **`import-table` requires a fresh, empty target table definition.**
  The import creates a new table; you cannot import into an existing
  table. The S3 source must be in the same region as the import. The
  input format (DynamoDB JSON or Parquet) must match the export
  format.

- **Cross-account backup via AWS Backup requires both KMS key policy
  and backup vault policy grants.** Sharing an encrypted backup cross-
  account needs the source account's KMS key policy to grant the
  recipient `kms:Decrypt` AND the destination backup vault policy to
  accept the source account. Without both, the copy fails at the
  encryption step.

- **AWS Backup Vault Lock (compliance mode) makes backups immutable.**
  A vault in Vault Lock `COMPLIANCE` mode cannot be deleted by anyone
  (including root) until the retention period expires. This is the
  recommended posture for ransomware-resilient DynamoDB backups. Use
  `GOVERNANCE` mode for softer guardrails (deletable with
  `backup:DismissGrant`).

## Recent AWS features (2024-2026) (moved from SKILL.md)


- **DynamoDB selective restore (2024-2025):** `restore-table-to-point-
  in-time` now supports attribute projection filters, allowing partial
  restores of specific keys/attributes. Reduces restore time and new-
  table cost when only a subset of data is needed. Verify the CLI
  version supports the `--restore-date-time` paired with the projection
  expression flags.

- **AWS Backup Vault Lock GA for DynamoDB (2024):** Vault Lock in
  COMPLIANCE mode makes DynamoDB backups immutable for the retention
  period — no one (including root) can delete early. Recommended for
  ransomware-resilient backups. Verify retention before locking.

- **Export to S3 with Parquet columnar format (2024):** Exports now
  support Parquet in addition to DynamoDB JSON, reducing S3 storage
  cost ~3-5x for large tables and enabling Athena/Glue analytics
  directly on the export.

- **Incremental export to S3 (2024-2025):** Exports now support an
  incremental mode that exports only items changed since a prior
  export, reducing export time and S3 cost for recurring backups.

- **Cross-account AWS Backup restore (2025):** AWS Backup now supports
  cross-account restore for DynamoDB, simplifying the KMS key policy
  coordination that previously made cross-account restore error-prone.

- **PITR cost visualization in AWS Cost Explorer (2024-2025):**
  DynamoDB PITR charges now broken out by table in Cost Explorer,
  making it easier to identify write-heavy tables driving PITR storage
  cost.

## Expert heuristic: backup cost vs table cost (moved from SKILL.md)


DynamoDB on-demand backups are billed at ~$0.10/GB-month for the
stored backup size — separately from and in addition to the table's
own storage cost. Backup cost scales LINEARLY with both table size and
retention count, which makes long-term backup retention in DynamoDB
the #1 DynamoDB cost surprise.

**Worked example — 1 TB table, daily backups, 30-day retention:**
- Table storage (Standard): 1 TB × $0.25/GB-month = $250/month.
- 30 backups × 1 TB × $0.10/GB-month = 30 TB-month × $0.10 = **$3,000/month**.
- Backups cost 12× the table itself.

**Decision rule — when to keep backups in DynamoDB vs S3:**

| Retention | Table size | Recommendation |
|---|---|---|
| <= 35 days | Any | Use PITR ($0.20/GB-month on change volume) — no separate backup management needed |
| 35-90 days | < 100 GB | On-demand backups in DynamoDB — simplicity outweighs cost |
| 35-90 days | >= 100 GB | S3 export via `export-table-to-point-in-time` — Parquet in S3 is ~95% cheaper |
| > 90 days | Any | ALWAYS use S3 export. Move to S3 Glacier Flexible Retrieval for compliance archives |

**S3 export cost model (2026):**
- One-time export: ~$0.008/GB read from DynamoDB + S3 storage
  ($0.023/GB Standard, $0.0036/GB Glacier Flexible Retrieval).
- 1 TB exported to Glacier: $8 export + $3.60/month storage — vs
  $100/month for a single DynamoDB backup.
- Incremental export (2024+) reduces repeat-export cost by ~90%.

**Action:** when an operator asks for "more backups" or "longer
retention" on a DynamoDB table, ALWAYS compute the backup-storage cost
and surface S3 export as the alternative. A blanket "keep 30 days of
daily backups" on a 500 GB table is a $1,500/month decision.

## Edge case: PITR restore and GSI rebuild cost (moved from SKILL.md)


`restore-table-to-point-in-time` and `restore-table-from-backup` copy
the GSI/LSI DEFINITIONS from the source — but the GSI data is rebuilt
as base-table data streams in. For large tables with many GSIs, this
creates two operational surprises:

1. **The restored table is not immediately queryable via GSIs.** Index
   status transitions `CREATING` → `BUILDING` → `ACTIVE`. Queries
   against a BUILDING GSI return stale or empty results. Monitor via
   `describe-table --query 'Table.GlobalSecondaryIndexes[*].{name:IndexName,status:IndexStatus}'`.
2. **The rebuild consumes write capacity on the restored table.** For
   PROVISIONED-mode restores, the rebuild burns the new table's
   provisioned WCU — if the operator copied the source's modest WCU,
   the rebuild takes hours-to-days. For PAY_PER_REQUEST restores, the
   rebuild bills at on-demand rates (~5x provisioned) — a 1 TB table
   with 3 GSIs can cost ~$1,000+ in rebuild write charges alone.

**Edge case — selective restore (2024+) and AWS Backup cross-region
restore may NOT recreate GSIs at all.** The selective-restore
projection filter and certain AWS Backup restore paths create the base
table only; GSI definitions must be added manually post-restore via
`update-table`. Plan for a manual GSI recreation step in the runbook.

**Diagnostic:** if a restored table appears to have no GSIs, run
`describe-table` and inspect `GlobalSecondaryIndexes`. If empty, add
each GSI manually:

```bash
aws dynamodb update-table \
  --table-name <restored-table> \
  --attribute-definitions AttributeName=pk,AttributeType=S AttributeName=sk1,AttributeType=S \
  --global-secondary-index-updates '[{"Create":{"IndexName":"gsi1","KeySchema":[{"AttributeName":"pk"},{"AttributeName":"sk1"}],"Projection":{"ProjectionType":"ALL"},"ProvisionedThroughput":{"ReadCapacityUnits":10,"WriteCapacityUnits":10}}}]'
```

**Fix:** for large tables, restore with `--billing-mode-override
PAY_PER_REQUEST` to let the rebuild consume whatever capacity it
needs, then switch to PROVISIONED once GSIs are ACTIVE and autoscaling
is registered.