# Diagnostic commands — macie-cost-optimizer

Data-gate and apply CLI listings moved verbatim from SKILL.md for progressive disclosure. Load on demand.

## Pre-flight data gate — required data sources (CLI list)

1. Macie membership / delegated administrator status: `aws macie2 get-macie-account` + `aws organizations list-delegated-administrators --service-principal macie.amazonaws.com`
2. Classification jobs: `aws macie2 list-classification-jobs` + `describe-classification-job` for each
3. Automated discovery status: `aws macie2 get-automated-discovery-configuration`
4. Bucket statistics: `aws macie2 get-bucket-statistics` + `aws macie2 list-buckets` (per Macie membership)
5. Classification scope (includes/excludes): `aws macie2 get-classification-scope`
6. Suppression rules: `aws macie2 list-sensitivity-inspection-templates` (filter for suppressions)
7. Cost Explorer Macie spend: `aws ce get-cost-and-usage --filter '{"Dimensions":{"Key":"SERVICE","Values":["Macie"]}}'`
8. Findings volume: `aws macie2 list-findings` + `get-findings` (sample for noise assessment)

## Step 3: applying the bucket exclusion (CLI)

**Applying the exclusion:**
```bash
aws macie2 update-classification-scope \
  --name <scope-name> \
  --s3 '{"excludes":{"bucketNames":["access-logs-prod","cloudtrail-archive","public-assets"]}}'
```
