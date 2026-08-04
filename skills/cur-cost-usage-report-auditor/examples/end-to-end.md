# End-to-end usage scenario: cur-cost-usage-report-auditor

A walkthrough showing the skill auditing a CUR that exists with a stale
delivery pipeline (STALE) and multiple config gaps (GZIP format, no Athena,
no versioning), demonstrating ordered classification, the staleness
threshold concept, and the per-dimension remediation workflow.

## Input (user prompt)

> Audit this CUR configuration before we start our quarterly cost
> optimization review. Our Athena cost queries have been returning
> empty results and I'm not sure if the pipeline is healthy.

```json
{
  "ReportDefinitions": [
    {
      "ReportName": "finops-cur-prod",
      "TimeUnit": "HOURLY",
      "Format": "textOrCsv",
      "Compression": "GZIP",
      "AdditionalSchemaElements": ["Resources"],
      "S3Bucket": "cur-bucket-prod",
      "S3Prefix": "cur/",
      "S3Region": "us-east-1",
      "AdditionalArtifacts": [],
      "RefreshClosedReports": false,
      "ReportVersion": "cur-1.0"
    }
  ]
}
```

S3 latest manifest timestamp: 2026-07-22T10:00:00Z (13 days ago)
S3 bucket versioning: Suspended

## Skill output

```text
REPORT: finops-cur-prod
VERDICT: STALE
REASON: Latest manifest is 13 days old for an hourly-cadence CUR (Step 2a)
— the delivery pipeline has definitively stopped. Multiple config gaps also
present: CSV/GZIP format blocks Athena, no ATHENA artifact, S3 versioning
suspended, and RefreshClosedReports disabled.
FINDINGS:
  - [HIGH] Hourly CUR manifest last delivered 13 days ago; staleness
    threshold is 48h (Step 2a)
  - [HIGH] Format is textOrCsv/GZIP — Athena integration is impossible (Step 3b)
  - [HIGH] AdditionalArtifacts does not include ATHENA — no crawler
    template generated (Step 3c)
  - [MEDIUM] S3 bucket versioning is Suspended — no point-in-time recovery
    for CUR data (Step 3d)
  - [MEDIUM] RefreshClosedReports is false — late corrections (refunds,
    credits, Savings Plans true-ups) never propagate (Step 3f)
  - [OK] ReportVersion is cur-1.0 — schema includes Savings Plans columns
  - [OK] AdditionalSchemaElements includes Resources — per-resource
    attribution is available
REMEDIATION:
  1. HIGH — Diagnose the stalled delivery: verify the S3 bucket policy
     grants billingreports.amazonaws.com PutObject + GetBucketAcl. Check
     if BillingViewArn points to a deleted view. If config is intact, open
     an AWS Support case (Billing category).
  2. HIGH — Update Format to Parquet and add ATHENA to AdditionalArtifacts:
     aws cur put-report-definition --report-definition file://updated-cur.json
     (set Format: Parquet, AdditionalArtifacts: ["ATHENA"])
  3. HIGH — After CUR resumes delivery, run the auto-generated CloudFormation
     crawler at s3://cur-bucket-prod/cur/finops-cur-prod/athena_integration/
     crawler-cfn.yml to create the Glue table. Verify with:
     aws glue get-table --database athenacur --name finops-cur-prod
  4. MEDIUM — Enable S3 versioning:
     aws s3api put-bucket-versioning --bucket cur-bucket-prod
     --versioning-configuration Status=Enabled
  5. MEDIUM — Set RefreshClosedReports to true in the updated definition
     so late billing corrections propagate.
  6. Back up the current definition before modifying:
     aws cur describe-report-definitions --output json >
     /tmp/cur-backup-$(date +%s).json
```

## What the skill caught that a generic assistant misses

1. **The staleness threshold is a hard number, not vibes.** A generic
   assistant says "the data seems old." The skill cites the 48-hour
   threshold for hourly cadence (6x the normal ~8h delivery window) and
   explains why 13 days is definitively a stopped pipeline, not slow
   delivery.

2. **CSV/GZIP blocks Athena — the format IS the integration.** A generic
   assistant mentions "you might want Parquet." The skill explains that
   Athena integration is structurally impossible with CSV format — the
   Glue crawler template requires Parquet columnar files. This is why
   the Athena queries are empty: there is no table and no queryable
   format.

3. **RefreshClosedReports causes silent reconciliation drift.** A generic
   assistant may not flag this at all. The skill identifies that
   `RefreshClosedReports: false` means refunds, credits, and Savings
   Plans true-ups for closed billing periods never propagate — the CUR
   will perpetually disagree with the Billing console.

4. **Ordered classification with all dimensions enumerated.** The verdict
   is STALE (worst finding), but the FINDINGS list shows every dimension:
   the delivery stall is HIGH, the Athena gap is HIGH, the versioning gap
   is MEDIUM, while the report version and Resources schema pass as OK.
   This lets the operator triage each dimension independently.

## Slash-command invocation

```
/aws:audit-cur-cost-usage-report
```

Or via the orchestrator:

```
/aws:pipeline
You: "audit our CUR before the cost optimization review"
```

The orchestrator emits
`[Phase: Audit | Skills routed: cur-cost-usage-report-auditor]` and hands
off to this skill for the VERDICT.

## Live-account follow-up (requires AWS CLI)

After remediating the configuration, validate the pipeline health:

```bash
# Confirm the updated report definition
aws cur describe-report-definitions --profile default --output json

# Verify CUR files are now arriving in S3
aws s3api list-objects-v2 --bucket cur-bucket-prod \
  --prefix cur/finops-cur-prod/ --profile default \
  --query 'reverse(sort_by(Contents,&LastModified))[0].LastModified'

# Confirm the Athena table exists after running the crawler CFN
aws glue get-table --database athenacur --name finops-cur-prod \
  --profile default --output json

# Verify versioning is enabled
aws s3api get-bucket-versioning --bucket cur-bucket-prod --profile default
```

Then run a test Athena query to confirm the pipeline end-to-end:

```sql
SELECT lineItem_ProductCode, SUM(lineItem_UnblendedCost) as cost
FROM athenacur.finops_cur_prod
WHERE year = '2026' AND month = '08'
GROUP BY lineItem_ProductCode
ORDER BY cost DESC
LIMIT 10;
```

Monitor for new manifest deliveries every 8 hours for the first 48 hours
to confirm the pipeline has resumed steady-state operation.
