---
description: Deploy an AWS Data Exchange data set with production-grade defaults (subscription creation, S3 asset export, revision auto-export via EventBridge, entitlement-based sharing, Lake Formation integration, API asset access, CloudWatch monitoring). Emits a READY_TO_DEPLOY checklist with verification commands.
nl_triggers:
  - "data exchange subscription"
  - "data exchange export"
  - "data exchange auto export"
  - "data exchange entitlement"
  - "data exchange job"
  - "data exchange lake formation"
  - "data exchange api asset"
  - "data exchange revision"
  - "data exchange s3 export"
  - "dataexchange dataset"
  - "subscribe to data product"
  - "export data exchange"
routes_to: dataexchange-dataset-deployer
---

# /aws:deploy-dataexchange-dataset

Activate the `dataexchange-dataset-deployer` skill and deploy an AWS
Data Exchange data set with production-grade defaults.

## What it does

The skill walks the provisioning procedure and emits a
READY_TO_DEPLOY checklist:

1. Subscription creation (data product from providers)
2. Asset structure (S3_SNAPSHOT, API, REDSHIFT_SNAPSHOT, QUERY)
3. Revision lifecycle (create, add assets, finalize, publish)
4. Asset export to S3 (export job creation)
5. Revision auto-export (EventBridge rule + Lambda orchestration)
6. Data set entitlement (sharing mechanism — NOT IAM)
7. Job creation (export and import job types)
8. Lake Formation integration (governed fine-grained access)
9. Auto-export to S3 for BI tools (QuickSight, partitioning)
10. API assets (REST endpoints as live data products)
11. CloudWatch monitoring (job status, stale data alarms)
12. Recent features (direct S3 access, API assets, Step Functions)

## When to use

- You need to subscribe to a Data Exchange data product.
- You need to export data exchange assets to S3.
- You need auto-export for new revisions.
- You need to share a data set with another AWS account.
- You need to create an export or import job.
- You need Lake Formation integration for governed data.
- You need to consume API assets as REST endpoints.
- You need CloudWatch monitoring for data freshness.

## How to invoke

### Slash command

```
/aws:deploy-dataexchange-dataset
```

Then provide: data set ID, subscription ID, asset type, revision ID,
destination S3 bucket, IAM role, auto-export requirements (if any),
Lake Formation details (if needed), entitlement target account (if
sharing), tags.

### Natural language

Any of these routes to the same skill:

- "subscribe to a data exchange data product"
- "export data exchange assets to my s3 bucket"
- "set up auto-export for new data exchange revisions"
- "share my data exchange data set with another account"
- "integrate data exchange with lake formation"

### CLI routing

```bash
node cli/bin/cli.js route "create data exchange export"
```

## Pipeline integration

This skill operates in **Phase 1 (Deploy)** of the CloudOps pipeline.
The orchestrator routes to it when the user wants to deploy Data
Exchange data pipelines. The output checklist feeds into verification
pipelines and downstream audit skills.

## Example

```
You: /aws:deploy-dataexchange-dataset

     Subscribe to Data Exchange data set ds-abc12345
     and export to my-analytics-bucket. Set up
     auto-export via EventBridge. Integrate with
     Lake Formation. Tags: Environment=production.

Skill:
  DATA_EXCHANGE: ds-abc12345 → S3: my-analytics-bucket
  VERDICT: READY_TO_DEPLOY
  CHECKLIST:
    [✓] Subscription: ACTIVE
    [✓] Export job: EXPORT_ASSETS_TO_S3
    [✓] Auto-export: EventBridge rule configured
    [✓] Lake Formation: table market_data registered
    [✓] Monitoring: stale data alarm configured
  VERIFICATION_COMMANDS:
    aws dataexchange get-data-set --data-set-id ds-abc12345 --region us-east-1
    aws dataexchange get-job --job-id <job-id> --region us-east-1
    aws events describe-rule --name DataExchangeAutoExport --region us-east-1
```

## References

- Skill definition: `skills/dataexchange-dataset-deployer/SKILL.md`
- Revision and export guide: `skills/dataexchange-dataset-deployer/references/revision-and-export.md`
- Entitlement and Lake Formation guide: `skills/dataexchange-dataset-deployer/references/entitlement-and-lake-formation.md`
- Eval suite: `skills/dataexchange-dataset-deployer/evals/evals.json`
