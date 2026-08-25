# Advanced Patterns — Athena Workgroup Auditor

Load-on-demand deep dives moved verbatim from SKILL.md: Step-0 expert knowledge, edge cases, remediation playbooks, workgroup internals, recent features.

## Step 0: Expert knowledge — non-obvious Athena behaviors that change classification

These behaviors are easy to misjudge without operational Athena experience.
Each changes a verdict if ignored:

- **`EnforceWorkGroupConfiguration` is a binary contract, not a
  suggestion.** When `true`, client-supplied `ResultConfiguration` in
  `StartQueryExecution` (OutputLocation, EncryptionConfiguration) is
  **silently ignored** — the caller cannot widen the workgroup's
  controls. When `false`, every client override is honored, including
  setting a different OutputLocation (potentially a bucket in another
  account for exfiltration), disabling encryption, or pointing at a
  weaker KMS key. A workgroup with `EnforceWorkGroupConfiguration: false`
  is a suggestion box, not a boundary. **This is the single most
  misunderstood Athena control** and the root cause of most "Athena
  cost-surprise" incidents.

- **`BytesScannedCutoffPerQuery` counts compressed S3 bytes IN, not
  uncompressed row count.** Parquet/ORC columnar pruning can reduce a
  1 TB table scan to 50 MB for a selective query; a CSV scan of the
  same table reads the full 1 TB. A DSL tuned for Parquet (e.g., 100 GB)
  will reject legitimate CSV analytical queries. Always consider source
  format when evaluating whether a DSL value is reasonable. Absent a
  DSL, a single `SELECT *` against an S3 Inventory export can scan
  double-digit TB.

- **`BytesScannedCutoffPerQuery` ABSENT ≠ 0.** The field is optional;
  absence means "no limit." A value of `0` also blocks every query
  (every scan exceeds 0 bytes) and is a misconfiguration, distinct from
  "no limit configured." Treat ABSENT as NO_LIMITS; treat `0` as
  CONFIG_GAP (the workgroup is non-functional).

- **`EncryptionConfiguration` covers OutputLocation writes only.** It
  does NOT encrypt:
  (1) CloudTrail logs of `StartQueryExecution` (those are CloudTrail's
  responsibility); (2) the source data in S3 / Glue Data Catalog
  (separate bucket encryption); (3) `GetQueryExecution` /
  `GetQueryResults` API responses (plaintext over TLS); (4) the
  workgroup metadata itself (account-level AWS-owned key); (5) named
  queries (`GetNamedQuery` returns plaintext SQL).
  So `EncryptionConfiguration: SSE_KMS` ≠ "all Athena data is
  encrypted" — only the result-set objects in S3 are. Be precise in
  the FINDINGS text; do not overstate coverage.

- **`SSE_S3` (S3-managed key) is still encryption at rest.** It is
  acceptable for many workgroups. However, it does NOT give you a
  CloudTrail data-event trail of KMS `Decrypt` calls (there are none —
  S3 manages the key), and it does NOT let you set a per-workgroup key
  policy. For compliance frameworks that require customer-managed keys
  (HIPAA, FedRAMP, PCI-DSS in some interpretations), note SSE_S3 as a
  COMPLIANCE_NOTE — do NOT classify as NO_ENCRYPTION.

- **Query history retention is NOT a workgroup setting.** Athena's
  `GetQueryExecution` / `ListQueryExecutions` APIs return a fixed
  **45-day rolling window** with no tunable parameter. There is no
  `QueryHistoryRetentionInDays` field — operators expecting "retain 7
  years of queries" via Athena are confused. Long-term retention
  requires shipping Athena events to CloudWatch Logs / S3 via CloudTrail
  (with long retention on the destination), or a CloudTrail Lake. A
  workgroup with no CloudTrail Athena data-event capture loses all
  query history past 45 days — flag as CONFIG_GAP.

- **`primary` workgroup is undeletable.** `DeleteWorkGroup` on `primary`
  returns `InvalidRequestException`. It is created automatically in
  every account in every region where Athena is activated. Its
  historical default is `EnforceWorkGroupConfiguration: false` with no
  OutputLocation, no encryption, no DSL — an open door for any principal
  with `athena:StartQueryExecution`. Always audit `primary` first; if
  it cannot be deleted, it must be locked down (`EnforceWorkGroupConfiguration: true`
  + SSE-KMS + DSL) or quarantined via IAM (`Deny` on
  `athena:StartQueryExecution` for `aws:ResourceTag/Workgroup = primary`
  — requires workgroup tagging, available post-2022).

- **Named queries persist SQL in plaintext.** `athena:CreateNamedQuery`
  stores the SQL string in the workgroup; `athena:GetNamedQuery` returns
  it verbatim. A named query containing hardcoded identifiers, customer
  IDs, or sensitive predicates is a data leak to any principal with
  `athena:GetNamedQuery` on the workgroup ARN. Named-query SQL is NOT
  encrypted by the workgroup's `EncryptionConfiguration`. Treat any
  named query accessible to `Principal: "*"` or a cross-account
  principal as a CONFIG_GAP finding.

- **`athena:GetQueryResults` is a data-exfiltration vector.** A
  principal with `athena:StartQueryExecution` + `athena:GetQueryResults`
  on a workgroup can run `SELECT * FROM sensitive_table` and read the
  entire result set, regardless of Glue Data Catalog fine-grained
  access control. The workgroup does not enforce column-level or
  row-level filters — only Lake Formation on the source table does.
  Scope `athena:GetQueryResults` to specific workgroups and named roles.

- **OutputLocation bucket policy must be aligned with the workgroup's
  EncryptionConfiguration.** If the bucket enforces SSE-KMS via a
  bucket policy (e.g., `s3:x-amz-server-side-encryption: aws:kms`
  deny-otherwise), a workgroup with `EncryptionConfiguration: SSE_S3`
  or absent will fail query execution at result write — the bucket
  rejects the plaintext or SSE-S3 PUT. The workgroup config must match
  the bucket policy. Mismatch manifests as silent query failures
  (`State: FAILED`, `StateChangeReason: ...AccessDenied...` on the S3
  PUT), not as a security verdict — flag as CONFIG_GAP for operational
  reliability.

- **Workgroup to KMS key policy coupling for SSE-KMS.** When the
  workgroup's `EncryptionConfiguration.EncryptionOption` is `SSE_KMS`
  or `CSE_KMS`, the named `KmsKey` MUST have a key policy permitting
  both `kms:GenerateDataKey` and `kms:Decrypt` to the Athena service
  principal `athena.<region>.amazonaws.com` (and, transitively, to the
  caller's role for result-read). Without this, query execution fails
  at the first result write with `AccessDeniedException` from KMS. This
  is the most common cause of "Athena SSE-KMS queries fail day 1"
  incidents.

- **Athena API quotas are account-region, not per-workgroup.**
  `StartQueryExecution` is rate-limited to ~100 concurrent queries per
  account-region by default (adjustable via Service Quotas). A
  workgroup without a DSL can saturate this quota with a single
  runaway `SELECT *` — the blast radius includes EVERY OTHER
  workgroup in the account-region (they queue behind the runaway).
  This is why NO_LIMITS is a HIGH-severity finding: it is not just
  cost, it is a cross-workgroup availability impact.

- **Spark workgroups ignore `BytesScannedCutoffPerQuery`.** When
  `EngineVersion` indicates AthenaSpark (notebook sessions), the DSL
  field has no effect — Spark compute is bounded by executor sizing,
  not SQL byte scans. A Spark workgroup with no DSL is NOT NO_LIMITS;
  it is CONFIG_GAP ("Spark sizing not bounded"). Confirm engine type
  before applying Step 4.

- **`PublishCloudWatchMetricsEnabled: false` is an observability gap,
  not a security verdict.** Flag as a note in FINDINGS but it does not
  drive the verdict — workgroup metrics are useful for DSL tuning, not
  for the verdict categories defined here.

- **Workgroup tags (post-2022) do NOT propagate to query results.**
  Tagging the workgroup does not tag the OutputLocation S3 objects.
  Object tags require an S3 lifecycle rule or Batch Operations. ABAC
  policies conditioned on `aws:ResourceTag/Environment` on the
  OutputLocation will not match workgroup tags.

- **Workgroup deletion is a soft delete.** `DeleteWorkGroup` on a
  workgroup with running queries leaves the queries to complete — they
  are not killed. The workgroup disappears from `ListWorkGroups`
  immediately for new queries. This is an availability risk during
  cleanup: a deletion mid-batch leaves the batch running with no
  visible workgroup to manage it.

## Edge-case handling

- **Partially malformed Configuration.** If the Configuration JSON parses
  but individual fields are missing (`ResultConfiguration`,
  `WorkGroupConfiguration`), classify each present dimension normally
  and emit an ERROR note for each malformed sub-block. Do NOT classify
  the entire workgroup as ERROR when only one sub-block is broken.

- **Workgroup with `ResultConfiguration.OutputLocation` absent but
  `EnforceWorkGroupConfiguration: true`.** Athena requires an
  OutputLocation to write results; if absent AND enforce=true, queries
  fail with `InvalidRequestException`. This is an operational config
  error — emit CONFIG_GAP (workgroup is non-functional), not
  NO_ENCRYPTION.

- **OutputLocation bucket enforces SSE-KMS via bucket policy, workgroup
  has SSE_S3 or absent encryption.** Queries fail at result-write time
  with `State: FAILED`, `StateChangeReason: ...AccessDenied...`. This
  is a CONFIG_GAP (operational mismatch), not NO_ENCRYPTION — the
  bucket policy is enforcing encryption; the workgroup is just
  misconfigured to mismatch it.

- **Spark workgroup with BytesScannedCutoffPerQuery set.** The DSL is a
  no-op for Spark sessions. Do NOT classify as OK on the limits
  dimension based on a set DSL — instead emit CONFIG_GAP ("DSL is
  ineffective for Spark engine; bound Spark sizing instead").

- **Workgroup `State: DISABLED` with controls absent.** The workgroup
  cannot run queries — the absent controls have no live blast radius.
  Emit VERDICT: OK with a STATE_NOTE: "Workgroup is DISABLED —
  findings inactive until re-enabled." Do not produce a NO_ENCRYPTION
  or NO_LIMITS verdict for a workgroup that cannot execute queries.

- **OutputLocation is a cross-account bucket.** The workgroup writes
  results to a bucket in another AWS account. Flag as CONFIG_GAP
  (results are outside the workgroup owner's control — the bucket
  owner can read, modify, or delete them; the workgroup's
  EncryptionConfiguration is still applied but the bucket policy
  governs access).

- **Workgroup with no named queries.** Step 6 returns no findings — the
  named-query dimension is OK by absence. Do not emit CONFIG_GAP for
  "no named queries" — it is a healthy state.

## Remediation guidance (playbooks per verdict)

### For NO_ENCRYPTION — EncryptionConfiguration absent

1. Identify the OutputLocation bucket. If absent, set one:
   `aws athena update-work-group --work-group <name>
   --configuration-updates ResultConfigurationUpdates={
   OutputLocation=s3://athena-results-<account>-<region>/}`
2. Create or identify a customer-managed KMS key in the workgroup's
   region. Verify the key policy grants `kms:GenerateDataKey` +
   `kms:Decrypt` to `athena.<region>.amazonaws.com`.
3. Enable SSE-KMS on the workgroup:
   `aws athena update-work-group --work-group <name>
   --configuration-updates ResultConfigurationUpdates={
   EncryptionConfiguration={EncryptionOption=SSE_KMS,
   KmsKey=arn:aws:kms:<region>:<account>:key/<id>}}`
4. Verify with `aws athena get-work-group --work-group <name>` —
   confirm `EncryptionConfiguration` is present.
5. If `EnforceWorkGroupConfiguration` is false, also flip it to true
   (see CONFIG_GAP enforcement remediation).
6. Re-encrypt or rotate any plaintext result objects already in the
   OutputLocation prefix from the exposure window — they remain
   readable to anyone with `s3:GetObject`.

### For NO_LIMITS — BytesScannedCutoffPerQuery absent

1. Inspect recent query statistics to calibrate the DSL:
   `aws athena list-query-executions --work-group <name>` → for each,
   `aws athena get-query-execution --query-execution-id <id>` →
   read `Statistics.DataScannedInBytes`.
2. Set the DSL to the 95th-percentile of recent scans, with a
   safety margin. For Parquet-backed analytical SQL, start at 1 TB
   (1099511627776 bytes); for CSV-backed, start at 100 GB
   (107374182400 bytes). Adjust down over time.
3. Apply:
   `aws athena update-work-group --work-group <name>
   --configuration-updates BytesScannedCutoffPerQuery=1099511627776`
4. Verify with `aws athena get-work-group` and confirm queries that
   would exceed the DSL now fail fast with
   `QueryExceedsBytesScannedLimit` (State: FAILED).
5. Consider CloudWatch alarm on `Microsoft.Athena` /
   `ProcessedBytes` metric to alert on queries approaching the DSL.

### For CONFIG_GAP — EnforceWorkGroupConfiguration false

1. **Before flipping**, enumerate every client pipeline that calls
   `StartQueryExecution` against this workgroup and check whether any
   passes a custom `ResultConfiguration`. Those callers will break
   silently post-flip — their overrides will be ignored.
2. Snapshot the current workgroup config (see Pre-flight safety).
3. Flip:
   `aws athena update-work-group --work-group <name>
   --configuration-updates EnforceWorkGroupConfiguration=true`
4. Verify with `aws athena get-work-group` — confirm the field reads
   `true`.
5. Monitor CloudTrail `StartQueryExecution` events for 1-2 weeks for
   `StateChangeReason` indicating config-override failures. Fix the
   client pipelines to rely on the workgroup's enforced config.

### For CONFIG_GAP — no CloudTrail Athena data events

1. Identify the CloudTrail trail capturing the workgroup's region
   (`aws cloudtrail describe-trails`).
2. Update the trail's `EventSelectors` or `AdvancedEventSelectors` to
   include Athena data events:
   `aws cloudtrail put-event-selectors --trail-name <trail>
   --event-selectors '[{...includeManagementEvents=true,
   ReadWriteTypeType=All, DataResources=[{Type="AWS::Athena::Workgroup",
   Values=["arn:aws:athena:<region>:<account>:workgroup/<name>"]}]}]'`
   For org trails, apply at the org level.
3. Verify with `aws cloudtrail get-event-selectors --trail-name <trail>`
   and confirm Athena data resources appear.
4. Set the trail's S3 destination bucket lifecycle to retain logs for
   the compliance horizon (e.g., 2555 days for 7-year retention).
5. For SQL-level query text retention past 45 days, also consider a
   CloudTrail Lake that includes `aws.athena` event sources.

### For CONFIG_GAP — named query IAM over-permissive

1. Identify the named queries:
   `aws athena list-named-queries --work-group <name>` → for each,
   `aws athena get-named-query --named-query-id <id>`.
2. For each named query containing sensitive SQL, scope the IAM grant
   to specific role ARNs:
   ```json
   {
     "Effect": "Allow",
     "Action": ["athena:GetNamedQuery", "athena:StartNamedQuery"],
     "Resource": "arn:aws:athena:<region>:<account>:workgroup/<name>",
     "Condition": {
       "StringEquals": {
         "aws:PrincipalArn": "arn:aws:iam::<account>:role/<specific-role>"
       }
     }
   }
   ```
3. Remove any `Principal: "*"` or cross-account grants on the
   workgroup ARN.
4. If the named query contains hardcoded identifiers, rotate them
   (assume leak during the exposure window) and replace with
   parameterized SQL via `athena:StartQueryExecution` with
   `ExecutionParameters` (Athena engine v3).

### For OK

1. No remediation required for the current posture.
2. Recommend verifying the KMS key policy still permits Athena
   (defense-in-depth — key policies drift).
3. Recommend verifying the OutputLocation bucket policy aligns with
   the workgroup's EncryptionConfiguration (operational reliability).
4. Recommend a periodic re-audit cadence (workgroup configs drift via
   `UpdateWorkGroup` from operators outside the security team).

## Deep reference: Athena workgroup internals

### Workgroup evaluation at query time

When a caller invokes `StartQueryExecution` with a `WorkGroup` and a
client-side `ResultConfiguration`, Athena evaluates the workgroup's
config in this order:

1. **`State`** — if `DISABLED`, reject with `InvalidRequestException`.
2. **`EnforceWorkGroupConfiguration`** — if `true`, ignore the
   client-supplied `ResultConfiguration` entirely; use the workgroup's
   `Configuration.ResultConfiguration`. If `false`, the client's
   `ResultConfiguration` (if present) overrides; fall back to the
   workgroup's config if the client omits a field.
3. **`BytesScannedCutoffPerQuery`** — applied regardless of the
   enforcement flag. The `StartQueryExecution` API has NO parameter
   for a per-query DSL override, so the workgroup's value is binding
   even when `EnforceWorkGroupConfiguration: false`. This is the one
   control that cannot be client-overridden via the query API. (Note:
   this is asymmetric with `ResultConfiguration`, which IS
   client-overridable when enforcement is off.)
4. **Engine routing** — if the workgroup engine is AthenaSpark, route
   to the Spark runtime (the DSL is ignored).

The implication for classification: **the DSL is the one control that
is binding even with `EnforceWorkGroupConfiguration: false`.** Update
Step 4 accordingly — a workgroup with enforcement=false BUT a DSL set
still has a binding DSL. However, encryption and OutputLocation remain
advisory. This does not change the verdict categories, but it does
change the FINDINGS text: do not say "DSL is advisory" — say "DSL is
binding but encryption/OutputLocation are advisory."

### Workgroup vs. IAM evaluation order

Effective permissions for an Athena query are computed as:

1. **Organizations SCP** — sets the maximum permissions.
2. **IAM identity-based policy** — must allow `athena:StartQueryExecution`
   + `athena:GetWorkGroup` on the workgroup ARN (+ optionally
   `athena:GetQueryResults`).
3. **Resource-based policy on the workgroup** (via
   `aws athena put-resource-policy`) — for cross-account workgroup
   sharing (rare). Both identity-based AND resource-based must allow.
4. **Workgroup Configuration** — applied at query time (the
   enforcement gate described above). This is NOT an IAM evaluation;
   it is a service-side configuration applied after IAM authorizes.
5. **Lake Formation** (on source Glue tables) — the only native
   row/column-level filter. The workgroup does NOT enforce
   column-level or row-level filters.

A caller authorized by IAM to run a query is NOT authorized to read
the source table unless Lake Formation (or Glue Data Catalog
fine-grained access) also permits. The workgroup cannot substitute
for Lake Formation — it governs result writes, not source reads.

### `primary` workgroup lifecycle

The `primary` workgroup is auto-created in every account-region where
Athena is activated. It cannot be deleted (`DeleteWorkGroup` returns
`InvalidRequestException` with `"Cannot delete workgroup primary"`).
Historical defaults (pre-2022):

- `EnforceWorkGroupConfiguration: false`
- No `ResultConfiguration.OutputLocation`
- No `EncryptionConfiguration`
- No `BytesScannedCutoffPerQuery`

Newer accounts (post-2022) may have `EnforceWorkGroupConfiguration: true`
with an auto-populated OutputLocation (`s3://aws-athena-query-results-<account>-<region>/`)
— but this is not guaranteed across all regions and partitions. Always
audit `primary` explicitly; do not assume defaults.

### Workgroup tagging (post-2022)

Workgroup tagging (`TagResource`, `UntagResource`, `ListTagsForResource`)
was added in 2022. Tags do NOT propagate to query results — the S3
objects in OutputLocation are tagged only by bucket lifecycle policy
or S3 Batch Operations. ABAC policies conditioned on
`aws:ResourceTag/Environment` on the OutputLocation will not match
workgroup tags.

### AthenaSpark workgroups

When `EngineVersion.SelectedEngineVersion` is `Athena Spark` (or the
workgroup has `AdditionalArtifacts` indicating notebook sessions),
the workgroup governs Spark compute sessions, not interactive SQL.
The `BytesScannedCutoffPerQuery` field has no effect. Spark sizing
is governed by session executor configuration, not by workgroup
Configuration. Treat Spark workgroups as a separate audit surface
(the verdict categories still apply, but the DSL evaluation is
skipped in favor of Spark sizing checks).

## Recent AWS features (2024-2026)

- **Athena capacity reservations (2024):** Workgroups can now be associated with capacity reservations for predictable query throughput. Auditors should check whether a workgroup has a capacity reservation attached and whether it matches expected workloads — unreserved workgroups may face throttling under concurrency limits.
- **Athena Spark and notebook workgroups (2024-2025):** Spark-enabled workgroups have different engine configurations than standard SQL workgroups. The BytesScannedCutoffPerQuery limit does not apply to Spark workgroups — instead, DPU limits apply. Auditors must check the engine version and apply the correct cost-control dimension.
- **Parameterized queries (2024):** Named queries can now accept parameters. This does not change the audit surface but means that IAM policy evaluation on `athena:StartQueryExecution` may need to account for parameterized query execution.
- **Cross-account workgroup queries:** Athena now supports cross-account access to workgroups via Lake Formation cross-account grants. Auditors should verify that cross-account workgroup access is intentional and bounded by Lake Formation permissions.
