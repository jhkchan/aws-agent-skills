---
name: dataexchange-dataset-deployer
description: 'Deploys AWS Data Exchange data sets with production defaults: subscription creation (data product from providers), asset export to S3, revision auto-export (EventBridge triggered on new data revision), data set entitlement (share with specific AWS accounts — entitlement is the sharing mechanism, NOT IAM), job creation (export jobs, import jobs), asset structure (S3 objects, DynamoDB tables, REST API assets), Lake Formation integration for governed data access, auto-export to S3 for BI tool consumption, revision lifecycle (create revision, add assets, finalize, publish), CloudWatch monitoring for job status and data freshness. Emits a READY_TO_DEPLOY checklist with verification commands. Use when subscribing. Triggers: create data exchange subscription, data exchange asset export, data exchange revision auto-export, data exchange entitlement, data exchange export job, data exchange import job, data exchange lake formation, data exchange API asset, data exchange revision lifecycle, data exchange S3...'
license: Apache-2.0
compatibility: 'Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). For live deployment: AWS CLI v2 with dataexchange and s3 access, plus EventBridge for auto-export rules. Works with Terraform aws_dataexchange_dataset / aws_dataexchange_revision resources and CloudFormation AWS::DataExchange::DataSet / AWS::DataExchange::Job templates.'
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: 'true'
  phase: '1'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: Analytics
  task_type: deploy
  skill_class: capability
  lifecycle_status: active
  verdict_shape: READY_TO_DEPLOY | PREREQUISITES_MISSING
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  tags: aws, data-exchange, analytics, cloudops, deploy, provisioning, subscription, revision, entitlement, auto-export, lake-formation, eventbridge
  dependencies: aws-orchestrator
  keywords: aws, data exchange, dataexchange, data set, dataset, subscription, analytics, cloudops, deploy, provisioning, revision, asset, entitlement, auto-export, lake formation, export job, api asset, eventbridge
  when_to_use: Invoke when the user wants to subscribe to an AWS Data Exchange data product, export data exchange assets to S3, set up auto- export for new revisions, share a data set with another AWS account via entitlement, create an export or import job, integrate Data Exchange with Lake Formation for governed data, consume API assets as REST endpoints, or configure revision auto-export with EventBridge. Do NOT invoke for AWS Glue data catalogs (use Glue skills), AWS Lake Formation table grants without Data Exchange (use Lake Formation skills), or S3 data transfer without Data Exchange (use S3 skills).
---

# Data Exchange Dataset Deployer

An AWS CloudOps agent skill that deploys AWS Data Exchange data sets
with correct defaults. The skill walks the operator through
subscription creation, asset structure (S3 objects, DynamoDB tables,
API assets), revision lifecycle (create, add assets, finalize,
publish), export job creation, auto-export rule configuration
(EventBridge triggered on new revisions), entitlement-based sharing
(NOT IAM), Lake Formation integration for governed access, and
CloudWatch monitoring for job status and data freshness, captures all
provisioning decisions, explains why each default matters, and emits
a READY_TO_DEPLOY checklist with copy-pasteable verification commands.

## Activation keywords

create Data Exchange subscription, Data Exchange asset export, Data
Exchange revision auto-export, Data Exchange entitlement, Data
Exchange export job, Data Exchange import job, Data Exchange Lake
Formation, Data Exchange API asset, Data Exchange revision lifecycle,
Data Exchange S3 auto-export.

## STRICT output contract

When this skill is invoked with a Data Exchange deployment request
(subscribe to a data product, export assets, set up auto-export,
share via entitlement, create a job, integrate Lake Formation, or a
partial configuration), the agent MUST respond with the
READY_TO_DEPLOY checklist defined in the "Output format" section
using the literal all-caps labels `DATA_EXCHANGE:`, `VERDICT:`,
`CHECKLIST:`, and `VERIFICATION_COMMANDS:`. Do NOT preface the
checklist with prose, headings, or disclaimers — emit the block as
the first lines of the response. This contract is what assertion-
based evals and downstream provisioning pipelines rely on; deviating
from the literal labels breaks automation silently.

If any prerequisite is missing, the verdict is
`PREREQUISITES_MISSING` with a specific gap citation in the
checklist (marked `[✗]`), and `READY_TO_DEPLOY` MUST NOT also
appear.

## Quick navigation

| Section | When to read |
|---|---|
| Prerequisites | Always — verify before provisioning |
| Step 1 — Subscription creation | Data product from providers |
| Step 2 — Asset structure | S3, DynamoDB, API assets |
| Step 3 — Revision lifecycle | Create, finalize, publish |
| Step 4 — Asset export to S3 | Export job creation |
| Step 5 — Revision auto-export (EventBridge) | Auto-export on new revision |
| Step 6 — Data set entitlement | Sharing mechanism |
| Step 7 — Job creation (export, import) | Job lifecycle |
| Step 8 — Lake Formation integration | Governed data access |
| Step 9 — Auto-export to S3 for BI tools | BI consumption |
| Step 10 — API assets (REST endpoints) | API as data product |
| Step 11 — CloudWatch monitoring | Job + freshness monitoring |
| Step 12 — Recent features | Latest |
| NEVER do these things | Review before signing off |
| Output format | The literal checklist template |
| references/revision-and-export.md | Revision + export detail |
| references/entitlement-and-lake-formation.md | Entitlement + LF detail |

## Mindset

Mindset framing and the three misconceptions (entitlements NOT IAM for sharing, revisions do NOT auto-export by default, export jobs are asynchronous) moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).
Load on demand before designing any Data Exchange configuration.

## Configuration dependency graph (novel heuristic)

Configuration dependency graph (subscription → data set → revision → assets → export job → auto-export rule → entitlement → Lake Formation → API asset) with hard-dependency, silent-failure, and downstream columns moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).
Load on demand to sequence provisioning in the correct order.

## Expert heuristic: auto-export revision rule

Auto-export heuristic (the 7-step EventBridge → Lambda → StartJob flow and the without-it failure mode) moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).
Load on demand when configuring revision auto-export.

## Expert heuristic: entitlement is the sharing mechanism

Entitlement heuristic (sharing decision tree: provider entitlement, Lake Formation for internal, S3 bucket policy post-export; entitlement-vs-IAM distinction) moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).
Load on demand when sharing a data set with another account.

## Expert heuristic: asset types determine export behavior

Asset-type heuristic (S3_SNAPSHOT exports to S3, REDSHIFT_SNAPSHOT restores to a cluster, API is live-only, QUERY is Lake Formation-backed) moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).
Load on demand when predicting export behavior per asset type.

## Prerequisites (verify before provisioning)

Before emitting provisioning commands, verify these prerequisites.
If any are missing, the verdict is **PREREQUISITES_MISSING**.

| Prerequisite | Why it matters | How to verify |
|---|---|---|
| Data product exists in marketplace | Subscription requires a valid product | `aws dataexchange list-data-sets` |
| Subscriber account approved | Some products require provider approval | Check subscription status |
| Destination S3 bucket exists | Export jobs write to a subscriber-owned S3 bucket | `aws s3 ls s3://<bucket>` |
| IAM role for export jobs | Export job needs s3:PutObject on destination bucket | Check IAM role policy |
| EventBridge rule (for auto-export) | Auto-export requires event-driven orchestration | `aws events list-rules --name-pattern "*dataexchange*"` |
| Lambda function (for auto-export) | EventBridge target that calls StartJob | `aws lambda list-functions` |
| Entitlement created (for sharing) | Sharing mechanism — NOT IAM | `aws dataexchange list-data-set-revisions` |
| Lake Formation enabled (for governed access) | LF controls fine-grained access | `aws lakeformation describe-resource` |
| Data Catalog database (for LF integration) | LF tables live in a Data Catalog database | `aws glue get-database --name <db>` |

If any prerequisite is missing, output
`VERDICT: PREREQUISITES_MISSING` and cite the specific gap.

## Step 1 — Subscription creation

A subscription grants access to a data product from a provider. The
data product contains one or more data sets.

Step 1 CLI listings (marketplace subscribe, list-data-sets, list-data-set-revisions, get-revision) moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md).
Load on demand when creating or inspecting a subscription.

**Subscription states:**

| State | Description |
|---|---|
| ACTIVE | Subscription is active; revisions accessible |
| EXPIRED | Subscription expired; no new revisions |
| CANCELED | Subscription canceled by subscriber or provider |

## Step 2 — Asset structure

Each revision in a data set contains assets. Asset types determine
how the data is consumed.

| Asset type | Content | Export destination | Auto-exportable |
|---|---|---|---|
| S3_SNAPSHOT | S3 objects (CSV, JSON, Parquet, etc.) | Subscriber's S3 bucket | YES |
| REDSHIFT_SNAPSHOT | Amazon Redshift cluster snapshot | Redshift (not S3) | NO |
| API | REST API endpoints (live access) | Data Exchange API gateway (live) | NO |
| QUERY | Lake Formation SQL query results | S3 (via LF) | YES |

Step 2 CLI listings (list-data-set-revisions, get-revision for asset discovery) moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md).
Load on demand when enumerating assets in a revision.

## Step 3 — Revision lifecycle

Revisions are versioned snapshots of the data set. Each revision
follows a lifecycle.

Step 3 revision-lifecycle text block (create → add assets → finalize → publish → export) and the create-revision / finalize-revision CLI moved verbatim to [references/revision-and-export.md](references/revision-and-export.md).
Load on demand when driving the provider revision lifecycle.

**Critical:** finalization is a ONE-WAY operation. Once finalized,
assets cannot be added or removed. Verify all assets are present
before finalizing.

## Step 4 — Asset export to S3

Export jobs copy S3_SNAPSHOT assets from the provider to the
subscriber's S3 bucket.

Step 4 CLI listings (start-job, create-job EXPORT_ASSETS_TO_S3 with AssetSources/Destination JSON, asynchronous get-job polling) moved verbatim to [references/revision-and-export.md](references/revision-and-export.md).
Load on demand when exporting assets to S3.

## Step 5 — Revision auto-export (EventBridge)

Auto-export delivers new revisions to the subscriber's S3 bucket
automatically. This requires an EventBridge rule + Lambda function.

Step 5 EventBridge rule CLI (put-rule on aws.dataexchange Data Update with data-set-id pattern) moved verbatim to [references/revision-and-export.md](references/revision-and-export.md).
Load on demand when wiring the auto-export trigger.

Step 5 auto-export Lambda function (boto3 create_job EXPORT_ASSETS_TO_S3 + start_job on revision events) moved verbatim to [references/revision-and-export.md](references/revision-and-export.md).
Load on demand when implementing the auto-export target.

Step 5 deploy CLI (events put-targets, lambda add-permission for EventBridgeInvoke) moved verbatim to [references/revision-and-export.md](references/revision-and-export.md).
Load on demand when deploying the auto-export orchestration.

## Step 6 — Data set entitlement

Entitlements are the sharing mechanism for Data Exchange. They
control which AWS accounts can access a data set. This is NOT done
via IAM.

Step 6 CLI listings (create-data-set via product listing, get-data-set Origin check) moved verbatim to [references/entitlement-and-lake-formation.md](references/entitlement-and-lake-formation.md).
Load on demand when creating or verifying an entitlement.

**Key:** entitlements grant account-level access to the data set.
Within the account, IAM controls which principals can call Data
Exchange APIs. Both are needed: entitlement (what data you can
access) + IAM (what API calls you can make).

## Step 7 — Job creation (export, import)

Data Exchange supports two job types:

| Job type | Description | Direction |
|---|---|---|
| EXPORT_ASSETS_TO_S3 | Copy assets from Data Exchange to subscriber S3 | Provider → Subscriber |
| IMPORT_ASSETS_FROM_S3 | Copy assets from subscriber S3 to Data Exchange (for providers publishing data) | Subscriber → Provider |

Step 7 export-job CLI (create-job/start-job/get-job sequence with AssetDestination JSON) moved verbatim to [references/revision-and-export.md](references/revision-and-export.md).
Load on demand when running the subscriber export flow.

**Job states:**

| State | Description |
|---|---|
| PENDING | Job created, not yet started |
| IN_PROGRESS | Job running |
| COMPLETED | Job finished successfully |
| ERROR | Job failed (check errors array) |
| CANCELLED | Job cancelled |

Step 7 import-job CLI (create-job IMPORT_ASSETS_FROM_S3 with AssetSources) moved verbatim to [references/revision-and-export.md](references/revision-and-export.md).
Load on demand when publishing data as a provider.

## Step 8 — Lake Formation integration

Lake Formation provides governed, fine-grained access to data
exported from Data Exchange. After exporting data to S3, register
the S3 location with Lake Formation and create a Data Catalog
table.

Step 8 CLI listings (lakeformation register-resource, glue create-database/create-table, lakeformation grant-permissions table and column-level) moved verbatim to [references/entitlement-and-lake-formation.md](references/entitlement-and-lake-formation.md).
Load on demand when configuring Lake Formation over exported data.

## Step 9 — Auto-export to S3 for BI tools

For BI tool consumption (QuickSight, Tableau, PowerBI), export
Data Exchange data to S3 in a BI-friendly format (CSV or Parquet)
and configure the BI tool to read from S3.

Step 9 BI Lambda (year=/month= partitioned auto-export to a BI bucket) moved verbatim to [references/revision-and-export.md](references/revision-and-export.md).
Load on demand when exporting for BI tool consumption.

**QuickSight integration:**

Point QuickSight to the exported S3 data:
- Create a QuickSight data set pointing to
  `s3://my-subscriber-bucket/bi-exports/`
- Enable SPICE (Super-fast, Parallel, In-memory Calculation Engine)
  for fast queries
- Schedule SPICE refresh to match Data Exchange revision cadence

## Step 10 — API assets (REST endpoints)

API assets provide live REST endpoints as data products. Unlike S3
assets, API assets are NOT exported — they are accessed live through
the Data Exchange API gateway.

Step 10 API-asset access code (get_asset, API gateway URL, Data Exchange signing) moved verbatim to [references/revision-and-export.md](references/revision-and-export.md).
Load on demand when consuming API assets live.

**Key differences from S3 assets:**

| Feature | S3_SNAPSHOT | API |
|---|---|---|
| Data freshness | Updated on revision publish | Live (real-time) |
| Export | Exported to subscriber S3 | NOT exported (accessed live) |
| Auto-export | YES (EventBridge rule) | NO (accessed on-demand) |
| Rate limiting | Unlimited (your S3) | Per-entitlement rate limits |
| Cost | Export + S3 storage | Per-API-call pricing |

## Step 11 — CloudWatch monitoring

Monitor Data Exchange job status and data freshness using
CloudWatch and EventBridge.

**CloudWatch metrics for Data Exchange:**

| Metric | Description |
|---|---|
| JobCount | Number of jobs by state |
| JobDuration | Job execution time |
| AssetCount | Number of assets per revision |
| RevisionAge | Time since last revision (custom metric) |

Step 11 monitoring CLI (job-completion EventBridge rule, RevisionAge stale-data alarm) moved verbatim to [references/entitlement-and-lake-formation.md](references/entitlement-and-lake-formation.md).
Load on demand when configuring production monitoring.

## Step 12 — Recent features

Recent AWS features (Data Exchange for S3, API assets, LF fine-grained access, EventBridge auto-export templates, API Gateway monetization, CloudWatch dashboards, Step Functions multi-step exports) moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).
Load on demand before recommending 2023-2026 capabilities.

## NEVER do these things

1. **NEVER use IAM policies as the sharing mechanism.** Entitlements
   control which accounts can access a data set, NOT IAM. IAM
   controls which principals within an account can call Data Exchange
   APIs. Both are needed, but only entitlements grant data set
   access.

2. **NEVER assume auto-export exists by default.** Without an
   EventBridge rule + Lambda, new revisions sit in Data Exchange
   and are never delivered to the subscriber's S3. Auto-export must
   be explicitly configured.

3. **NEVER treat export jobs as synchronous.** Export jobs are
   asynchronous and can take minutes to hours. Poll job status or
   use EventBridge to trigger downstream processing only after
   COMPLETED status.

4. **NEVER try to export API assets to S3.** API assets are accessed
   live through the Data Exchange API gateway. S3 auto-export rules
   do not apply to API assets.

5. **NEVER finalize a revision before all assets are added.**
   Finalization is a one-way operation. Once finalized, assets
   cannot be added, modified, or removed. Verify asset completeness
   before finalizing.

6. **NEVER skip the destination S3 bucket IAM policy.** The export
   job assumes a role that needs `s3:PutObject` on the destination
   bucket. Without this, the job fails silently (state: ERROR with
   an IAM error in the details).

7. **NEVER configure Lake Formation grants without first exporting
   data to S3.** Lake Formation governs data in the Data Catalog,
   which reads from S3. The data must be exported from Data Exchange
   to S3 before LF grants can apply.

8. **NEVER assume Redshift snapshot assets export to S3.**
   REDSHIFT_SNAPSHOT assets are restored to a Redshift cluster,
   not exported to S3. The subscriber must have a Redshift cluster
   to consume these assets.

9. **NEVER hardcode revision IDs in downstream pipelines.** Revision
   IDs change with each new revision. Use EventBridge events or the
   ListRevisions API to dynamically discover the latest revision.

10. **NEVER skip CloudWatch monitoring for production data
    pipelines.** Set up alarms for stale data (no revision in N
    days), job failures, and export duration anomalies. Data
    freshness SLAs require proactive monitoring.

## Output format

```text
DATA_EXCHANGE: <data-set-id> (subscription: <subscription-id>) → S3: <destination-bucket>
VERDICT: READY_TO_DEPLOY | PREREQUISITES_MISSING
CHECKLIST:
  [✓|✗] Subscription: <subscription-id> — ACTIVE
  [✓|✗] Data set: <data-set-id> — <asset-type> (S3_SNAPSHOT | API | REDSHIFT_SNAPSHOT | QUERY)
  [✓|✗] Revision: <revision-id> — FINALIZED
  [✓|✗] Assets: <count> assets of type <asset-type>
  [✓|✗] Destination S3 bucket: <bucket-name> — exists
  [✓|✗] IAM role: export job role with s3:PutObject on <bucket> — configured
  [✓|✗] Export job: <job-id> — type EXPORT_ASSETS_TO_S3
  [✓|✗] Auto-export: EventBridge rule "<rule-name>" → Lambda "<function-name>" — configured | not configured
  [✓|✗] Entitlement: target account <account-id> — entitled | not required
  [✓|✗] Lake Formation: S3 location registered, Data Catalog table "<table-name>" — configured | not required
  [✓|✗] API asset access: <api-url> — live access via Data Exchange gateway | not applicable
  [✓|✗] CloudWatch monitoring: job status alarm + stale data alarm — configured
  [✓|✗] Tags: <key=value list>
VERIFICATION_COMMANDS:
  aws dataexchange get-data-set --data-set-id <data-set-id> --region <region>
  aws dataexchange get-job --job-id <job-id> --region <region>
  aws events describe-rule --name <rule-name> --region <region>
```

### Worked example — S3 auto-export with Lake Formation

```text
DATA_EXCHANGE: ds-abc12345 (subscription: sub-def67890) → S3: my-analytics-bucket
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓] Subscription: sub-def67890 — ACTIVE
  [✓] Data set: ds-abc12345 — S3_SNAPSHOT (CSV files)
  [✓] Revision: r-ghi11122 — FINALIZED
  [✓] Assets: 5 assets of type S3_SNAPSHOT
  [✓] Destination S3 bucket: my-analytics-bucket — exists
  [✓] IAM role: dx-export-role with s3:PutObject on my-analytics-bucket — configured
  [✓] Export job: j-xyz33344 — type EXPORT_ASSETS_TO_S3
  [✓] Auto-export: EventBridge rule "DataExchangeAutoExport" → Lambda "dx-auto-export" — configured
  [✓] Entitlement: not required (same account)
  [✓] Lake Formation: S3 location registered, Data Catalog table "market_data" — configured
  [✓] API asset access: not applicable
  [✓] CloudWatch monitoring: job status alarm + stale data alarm (7 days) — configured
  [✓] Tags: Environment=production, DataSource=market-data
VERIFICATION_COMMANDS:
  aws dataexchange get-data-set --data-set-id ds-abc12345 --region us-east-1
  aws dataexchange get-job --job-id j-xyz33344 --region us-east-1
  aws events describe-rule --name DataExchangeAutoExport --region us-east-1
```

## Error handling

Error-handling deep dives (export job ERROR, auto-export not triggering, revision invisible to subscriber, LF table inaccessible, API authentication failures) moved verbatim to [references/error-handling.md](references/error-handling.md).
Load on demand when a deployment or job fails.

## References (load on demand)

- [references/advanced-patterns.md](references/advanced-patterns.md) — Mindset misconceptions, configuration dependency graph, expert heuristics, and Recent AWS features moved from SKILL.md
- [references/diagnostic-commands.md](references/diagnostic-commands.md) — subscription and revision/asset listing CLI moved from SKILL.md
- [references/error-handling.md](references/error-handling.md) — failure-mode deep dives moved from SKILL.md
- [references/revision-and-export.md](references/revision-and-export.md) — revision lifecycle, export/import jobs, auto-export orchestration, BI/API asset code moved from SKILL.md (pre-existing; extended)
- [references/entitlement-and-lake-formation.md](references/entitlement-and-lake-formation.md) — entitlement, Lake Formation, and monitoring CLI moved from SKILL.md (pre-existing; extended)

## Domain

AWS CloudOps / AWS Data Exchange Data Set Subscription, Export, and
Governed Analytics.

## AWS documentation

- **Data Exchange User Guide** — https://docs.aws.amazon.com/data-exchange/latest/userguide/what-is.html
- **Subscribing to data products** — https://docs.aws.amazon.com/data-exchange/latest/userguide/subscribe-to-data-sets.html
- **Exporting assets** — https://docs.aws.amazon.com/data-exchange/latest/userguide/export-jobs.html
- **Auto-export** — https://docs.aws.amazon.com/data-exchange/latest/userguide/auto-export.html
- **Entitlements** — https://docs.aws.amazon.com/data-exchange/latest/userguide/entitlements.html
- **API assets** — https://docs.aws.amazon.com/data-exchange/latest/userguide/api-assets.html
- **Lake Formation integration** — https://docs.aws.amazon.com/data-exchange/latest/userguide/lake-formation.html
- **Job lifecycle** — https://docs.aws.amazon.com/data-exchange/latest/userguide/jobs.html
- **EventBridge events** — https://docs.aws.amazon.com/data-exchange/latest/userguide/event-bridge.html
- **CloudWatch monitoring** — https://docs.aws.amazon.com/data-exchange/latest/userguide/monitoring.html
