# Advanced Patterns (load on demand) — DynamoDB Table Auditor

Step 0 expert-knowledge behaviors, capacity and recovery internals, and recent AWS features moved verbatim from SKILL.md. Loaded on demand.

---

## Step 0: Expert knowledge — non-obvious DynamoDB behaviors (moved from SKILL.md)

These behaviors are easy to misjudge without operational DynamoDB experience.
Each changes the verdict if ignored:

- **DynamoDB ALWAYS encrypts at rest — "UNENCRYPTED" means no customer KMS
  control, not plaintext.** The default SSEType AES256 uses an AWS-owned key
  with no CloudTrail Decrypt events, no key policy, no rotation visibility. For
  compliance (PCI-DSS req 3.4, HIPAA §164.312(a)(2)(iv), SOC2 CC6.1), this is a
  finding. Do NOT tell the operator "your data is plaintext" — it is not. Tell
  them they have no audit trail or control over the encryption key.

- **PITR and AWS Backup are different recovery mechanisms.** PITR
  (ContinuousBackupsStatus: ENABLED) provides a 35-day continuous replay — you
  can restore to any second within the window. AWS Backup takes scheduled
  snapshots at intervals you define. A table with AWS Backup but no PITR cannot
  recover data written and then accidentally deleted between snapshots. They
  are complementary, not substitutive.

- **GSI throttling cascades to the base table.** A GSI with insufficient RCUs
  causes `ProvisionedThroughputExceededException` on writes to the BASE TABLE —
  even if the base table has ample capacity. DynamoDB enforces GSI consistency
  by throttling base-table writes when any GSI falls behind. A PROVISIONED
  table with autoscaling on the base table but NOT on a GSI is a
  CAPACITY_MISMATCH — the GSI is the throttle origin.

- **LSI 10 GB per-partition limit is a silent failure.** An LSI has a hard 10
  GB-per-partition size limit. When exceeded, writes to items in that partition
  are silently rejected with no CloudWatch alarm (unless you build one). The
  base table has no analogous limit. Flag LSI presence as a CONFIG_GAP on
  growing tables — the operator must monitor per-partition index size.

- **LSI can ONLY be created at table creation time.** You cannot add an LSI to
  an existing table — this is a hard API constraint. If a table has zero LSIs
  and the workload needs a new alternate key, the operator must create a new
  table and migrate. This makes LSI absence (or insufficiency) an architectural
  concern, not an operational fix.

- **GSI quota: 20 per table (soft limit), LSI: 5 per table (HARD limit).** The
  20-GSI soft limit can be raised via a support ticket. The 5-LSI hard limit
  cannot be increased — it is enforced at the API level. A table at 18 GSIs is
  approaching the soft ceiling and should be flagged as CONFIG_GAP.

- **TTL is not real-time deletion.** TTL items are deleted by a background
  scanner within **48 hours** of the expiry timestamp. Items remain readable
  and queryable until physically deleted. For GDPR / data-retention compliance,
  you cannot rely on TTL for immediate data deletion — it is a cost-optimization
  feature, not a compliance enforcement mechanism.

- **On-demand burst capacity is finite.** On-demand mode allocates burst
  capacity based on the trailing 30 minutes of traffic (the "burst bucket"). A
  cold-start spike from zero traffic can still throttle if the burst bucket is
  empty. On-demand is NOT "instant unlimited" — it is "instant for recent
  traffic levels."

- **Provisioned autoscaling has a 3-5 minute reaction lag.** Target-tracking
  autoscaling uses a CloudWatch alarm with a 2-minute evaluation period plus a
  warm-up window. For sub-minute traffic spikes, PROVISIONED + autoscaling
  will throttle before scaling completes. On-demand is the correct choice for
  unpredictable burst patterns.

- **SSE-KMS with a customer CMK adds a KMS dependency cascade.** Every
  DynamoDB operation with SSE-KMS involves a KMS Decrypt call (cached for ~5
  minutes via data-key reuse). If KMS throttles or the key is disabled, all
  DynamoDB operations on the table fail. AWS-managed keys (`alias/aws/dynamodb`)
  have higher service quotas and DynamoDB manages the lifecycle internally — but
  give you no policy control. This is the trade-off the operator must
  understand.

- **PITR restore creates a NEW table, not a rewind.** `RestoreTableToPointInTime`
  creates a new table — it cannot overwrite the original. The restored table
  inherits schema and indexes from the source but gets DEFAULT capacity settings
  (you must reconfigure capacity after restore). Plan for application cutover:
  update endpoints, validate data, then delete the old table.

- **BillingMode switch has a cooldown.** You can switch between PROVISIONED and
  PAY_PER_REQUEST, but DynamoDB enforces a cooldown (~minutes) between switches.
  Frequent switching for cost optimization does not work — DynamoDB prevents
  capacity-gaming. Choose a mode based on traffic profile, not per-request cost.

- **DeletionProtectionEnabled is the last line of defense.** When true, the
  table cannot be deleted via `delete-table` — the API returns
  `ResourceInUseException`. This protects against accidental deletion and
  ransomware scenarios. Added in November 2023 — many legacy tables predate it.

---

## Deep reference: DynamoDB capacity and recovery internals (moved from SKILL.md)

### On-demand burst capacity

On-demand mode maintains a burst capacity bucket sized to the trailing
30-minute traffic average × 5 (approximately). A table that sustains 1,000
RCU/sec builds a burst bucket of ~5,000 RCU/sec for short spikes. A cold-start
table (zero recent traffic) has an empty burst bucket — the first spike may
throttle while DynamoDB warms up. This is why on-demand is NOT recommended for
traffic patterns with prolonged zero-then-spike cycles (e.g., a batch job that
runs once per hour).

### Provisioned autoscaling timing

Target-tracking autoscaling evaluates a CloudWatch alarm every 1 minute with a
2-minute evaluation period. When the alarm fires (utilization > target for 2
consecutive minutes), autoscaling issues a scale-out. The new capacity takes
effect within seconds of the API call, but the alarm → evaluation → action
pipeline takes 3-5 minutes. For traffic spikes that ramp faster than 3 minutes,
PROVISIONED + autoscaling will throttle before scaling completes.

### PITR restore mechanics

`RestoreTableToPointInTime` creates a new table from the source table's
continuous backup. Key constraints:

- The restored table name must be unique (cannot overwrite the source).
- The restored table gets DEFAULT capacity settings — not the source's settings.
  You must reconfigure capacity (or switch to on-demand) after restore completes.
- The restore is asynchronous — large tables take minutes to hours depending
  on size. The table is not available until `TableStatus` transitions from
  `RESTORING` to `ACTIVE`.
- Indexes (GSI/LSI) from the source are recreated on the restored table.

### GSI write-capacity model

A GSI in PROVISIONED mode has its own RCU/WCU allocation, separate from the
base table. DynamoDB asynchronously replicates base-table writes to the GSI
using the GSI's WCU. If the GSI's WCU is insufficient, the replication falls
behind, and DynamoDB throttles base-table writes to prevent unbounded GSI lag.
This is why GSI autoscaling is not optional in PROVISIONED mode — it is the
only way to prevent cascade throttling under variable write load.

### SSE-KMS data-key caching

When SSE-KMS is enabled, DynamoDB generates a data key per partition via KMS
`GenerateDataKey` and caches it for approximately 5 minutes. Within the cache
window, no KMS API call is needed. After the cache expires, DynamoDB calls KMS
again. This means:

- KMS API rate limits apply: a table with thousands of active partitions can
  generate significant KMS traffic. Customer-managed CMKs share the account's
  KMS rate quota; AWS-managed keys (`aws/dynamodb`) have a dedicated quota.
- KMS key disablement takes 5 minutes to take effect on DynamoDB (the cache
  window). Plan for this delay when rotating or disabling keys.

---

## Recent AWS features (2024-2026) (moved from SKILL.md)

- **DynamoDB table classes — Standard and Standard-IA (2024):** Tables can now be assigned the `STANDARD` or `STANDARD_INFREQUENT_ACCESS` table class. Auditors should verify that infrequently accessed tables use Standard-IA for cost optimization, and that high-throughput tables remain on Standard.
- **Incremental export to S3 (2024):** DynamoDB now supports incremental exports to S3 in addition to full-table exports. Auditors should verify that export-to-S3 is configured with appropriate KMS encryption and that the S3 destination bucket has lifecycle policies.
- **Amazon Q integration (2024-2025):** DynamoDB now integrates with Amazon Q for natural-language queries. No direct audit-surface change, but auditors should verify that Q integration does not grant unexpected IAM access to table data.
- **Global Tables v2 replication enhancements (2024):** Improved global tables with faster replication and new CloudWatch metrics for replication latency. Auditors should verify that replication alarms are configured on `ReplicationLatency` for multi-region tables.
