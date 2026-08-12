# End-to-End Example: Data Exchange Dataset Deployment

A walkthrough showing how to use the `dataexchange-dataset-deployer`
skill from invocation through verification. Mirrors the structured-
eval pattern of shipping a concrete worked example per skill.

---

## Scenario

You are subscribing to a market data product on AWS Data Exchange,
configuring auto-export to deliver new revisions to your S3 bucket,
integrating with Lake Formation for governed access, and setting up
CloudWatch monitoring. The setup needs:

- Data set: ds-abc12345 (S3_SNAPSHOT, CSV market data)
- Subscription: sub-def67890 (ACTIVE)
- Revision: r-ghi11122 (FINALIZED, 5 assets)
- Destination S3 bucket: my-analytics-bucket
- Auto-export: EventBridge rule + Lambda
- Lake Formation: Data Catalog table market_data
- CloudWatch: stale data alarm + job failure notification
- Tags: Environment=production, DataSource=market-data

---

## Step 1 — Invoke the skill

### Option A: Slash command

```
/aws:deploy-dataexchange-dataset
```

Then paste the requirements.

### Option B: Natural language

```
You: "Subscribe to Data Exchange data set ds-abc12345
      and set up auto-export to my-analytics-bucket.
      Integrate with Lake Formation for governed access.
      Set up CloudWatch monitoring for stale data."
```

### Option C: CLI routing

```bash
node cli/bin/cli.js route "create data exchange export"
```

---

## Step 2 — Skill produces the READY_TO_DEPLOY checklist

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
  [✓] Export job: type EXPORT_ASSETS_TO_S3
  [✓] Auto-export: EventBridge rule "DataExchangeAutoExport" → Lambda "dx-auto-export" — configured
  [✓] Entitlement: not required (same account)
  [✓] Lake Formation: S3 location registered, Data Catalog table "market_data" — configured
  [✓] API asset access: not applicable
  [✓] CloudWatch monitoring: job status alarm + stale data alarm (7 days) — configured
  [✓] Tags: Environment=production, DataSource=market-data
VERIFICATION_COMMANDS:
  aws dataexchange get-data-set --data-set-id ds-abc12345 --region us-east-1
  aws dataexchange get-job --job-id <job-id> --region us-east-1
  aws events describe-rule --name DataExchangeAutoExport --region us-east-1
```

---

## Step 3 — Create the initial export job

```bash
# Create and start the export job for the current revision
JOB_ID=$(aws dataexchange create-job \
  --type EXPORT_ASSETS_TO_S3 \
  --details '{
    "ExportAssetsToS3": {
      "DataSetId": "ds-abc12345",
      "RevisionId": "r-ghi11122",
      "AssetDestination": {
        "Bucket": "my-analytics-bucket",
        "Key": "data-exchange/exports/"
      }
    }
  }' \
  --query 'Id' --output text \
  --region us-east-1)

aws dataexchange start-job \
  --job-id "$JOB_ID" \
  --region us-east-1

# Poll for completion
aws dataexchange get-job \
  --job-id "$JOB_ID" \
  --region us-east-1
# Expected: state: COMPLETED
```

---

## Step 4 — Set up auto-export (EventBridge + Lambda)

```bash
# Create EventBridge rule for Data Update events
aws events put-rule \
  --name "DataExchangeAutoExport" \
  --event-pattern '{
    "source": ["aws.dataexchange"],
    "detail-type": ["Data Update"],
    "detail": {
      "data-set-id": ["ds-abc12345"]
    }
  }' \
  --region us-east-1

# Deploy the Lambda function (see references/revision-and-export.md for code)
aws lambda create-function \
  --function-name dx-auto-export \
  --runtime python3.12 \
  --role arn:aws:iam::123456789012:role/lambda-dx-role \
  --handler index.lambda_handler \
  --zip-file fileb://dx-auto-export.zip \
  --environment "Variables={DESTINATION_BUCKET=my-analytics-bucket,DATA_SET_ID=ds-abc12345}" \
  --region us-east-1

# Add EventBridge target
aws events put-targets \
  --rule "DataExchangeAutoExport" \
  --targets '[{"Id": "1", "Arn": "arn:aws:lambda:us-east-1:123456789012:function:dx-auto-export"}]' \
  --region us-east-1

# Grant EventBridge permission to invoke Lambda
aws lambda add-permission \
  --function-name dx-auto-export \
  --statement-id EventBridgeInvoke \
  --action lambda:InvokeFunction \
  --principal events.amazonaws.com \
  --region us-east-1
```

---

## Step 5 — Register with Lake Formation

```bash
# Register S3 location with Lake Formation
aws lakeformation register-resource \
  --resource-arn "arn:aws:s3:::my-analytics-bucket/data-exchange/" \
  --role-arn "arn:aws:iam::123456789012:role/LFServiceRole" \
  --region us-east-1

# Run Glue Crawler to discover schema
aws glue start-crawler \
  --name dx-crawler \
  --region us-east-1

# Grant SELECT on the table to analyst role
aws lakeformation grant-permissions \
  --principal '{"DataLakePrincipalIdentifier": "arn:aws:iam::123456789012:role/AnalystRole"}' \
  --permissions ["SELECT"] \
  --resource '{"Table": {"DatabaseName": "data_exchange_db", "Name": "market_data"}}' \
  --region us-east-1
```

---

## Step 6 — Set up CloudWatch monitoring

```bash
# Stale data alarm (no revision in 7 days)
aws cloudwatch put-metric-alarm \
  --alarm-name "DataExchangeStaleData" \
  --metric-name RevisionAge \
  --namespace DataExchange \
  --statistic Maximum \
  --period 86400 \
  --threshold 7 \
  --comparison-operator GreaterThanThreshold \
  --evaluation-periods 1 \
  --alarm-actions ["arn:aws:sns:us-east-1:123456789012:data-alerts"] \
  --region us-east-1

# Job failure notification
aws events put-rule \
  --name "DataExchangeJobFailed" \
  --event-pattern '{
    "source": ["aws.dataexchange"],
    "detail-type": ["Job Status Change"],
    "detail": {"state": ["ERROR"]}
  }' \
  --region us-east-1

aws events put-targets \
  --rule "DataExchangeJobFailed" \
  --targets '[{"Id": "1", "Arn": "arn:aws:sns:us-east-1:123456789012:dx-alerts"}]' \
  --region us-east-1
```

---

## Step 7 — Post-deployment verification

```bash
# Data set is accessible
aws dataexchange get-data-set \
  --data-set-id ds-abc12345 \
  --region us-east-1

# Export job completed
aws dataexchange get-job \
  --job-id "$JOB_ID" \
  --region us-east-1

# Auto-export rule is active
aws events describe-rule \
  --name DataExchangeAutoExport \
  --region us-east-1

# Data is in S3
aws s3 ls s3://my-analytics-bucket/data-exchange/exports/

# Lake Formation table is queryable
aws athena start-query-execution \
  --query-string "SELECT COUNT(*) FROM data_exchange_db.market_data" \
  --query-execution-context '{"Database": "data_exchange_db"}' \
  --result-configuration '{"OutputLocation": "s3://my-query-results/athena/"}' \
  --region us-east-1
```

---

## What the skill catches that a naive provisioning misses

| Configuration | Naive provisioning | Skill output | Why the skill is right |
|---|---|---|---|
| Auto-export | Assumes default auto-export | EventBridge rule + Lambda orchestration | Auto-export is NOT built-in; must be explicitly configured |
| Job asynchronicity | Reads S3 immediately after CreateJob | Polls job status or uses EventBridge | Export jobs are asynchronous; immediate reads fail |
| Entitlement vs IAM | Uses IAM bucket policy for sharing | Entitlement is the sharing mechanism | IAM does not grant data set access; entitlements do |
| API assets | Tries to export API to S3 | API accessed live via DX gateway | API assets are live endpoints, not exportable |
| Revision finalization | Exports DRAFT revision | Verifies FINALIZED state first | Only FINALIZED revisions can be exported |
| Lake Formation | Creates table without registering S3 | Register S3 location first, then create table | LF requires S3 location registration before grants |
| Data freshness | No monitoring | CloudWatch stale data alarm (7 days) | Without monitoring, stale data goes undetected |

---

## Related artifacts

- **Skill definition:** `skills/dataexchange-dataset-deployer/SKILL.md`
- **Revision and export guide:** `skills/dataexchange-dataset-deployer/references/revision-and-export.md`
- **Entitlement and Lake Formation guide:** `skills/dataexchange-dataset-deployer/references/entitlement-and-lake-formation.md`
- **Slash command:** `commands/aws/deploy-dataexchange-dataset.md`
- **Eval suite:** `skills/dataexchange-dataset-deployer/evals/evals.json`
- **Legacy test cases:** `skills/dataexchange-dataset-deployer/eval/test-cases.yaml`
