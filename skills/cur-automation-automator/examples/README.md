# End-to-end usage scenario: cur-automation-automator

A walkthrough showing the skill designing a greenfield CUR + Athena
automation stack on a payer account, then surfacing a
MANUAL_STEP_REQUIRED verdict when a linked (member) account tries to
create an organization-wide CUR. Each path includes requirement
checks, full template emission, and post-verification guidance —
contrasted with what a generic assistant misses.

## Input (user prompt)

> Set up CUR with Athena for prod-cur-automation. Caller is the payer
> account 111111111111. CUR bucket is `prod-cur-bucket` in us-east-1
> with the right bucket policy already. Hourly granularity with
> resource-level data, Parquet format. Create a Glue database
> `prod_cur` and a non-primary Athena workgroup `finops-cur` with
> 1 TB DSL. Also wire up a daily top-spenders query.

```json
{
  "Operation": "create",
  "Stack name": "prod-cur-automation",
  "Caller": "payer account 111111111111",
  "CUR bucket": "prod-cur-bucket",
  "Granularity": "HOURLY",
  "Resource-level": true,
  "Format": "Parquet",
  "ReportVersioning": "CREATE_NEW",
  "RequirementChecks": {
    "organizations.describe-organization": {"MasterAccountId": "111111111111"},
    "sts.get-caller-identity": {"Account": "111111111111"},
    "cur.describe-report-definitions": [],
    "s3api.get-bucket-location.prod-cur-bucket": {"LocationConstraint": "us-east-1"},
    "s3api.get-bucket-policy.prod-cur-bucket": {
      "Statement[0].Principal.Service": "billingreports.amazonaws.com",
      "Statement[1].Principal.Service": "athena.amazonaws.com"
    },
    "glue.get-database.prod_cur": {"Status": "EntityNotFoundException"},
    "athena.list-work-groups": ["primary"]
  }
}
```

## Skill output — AUTOMATED

```text
OPERATION: create
VERDICT: AUTOMATED
TARGET: prod-cur-automation
REQUIREMENTS:
  - [PASS] Caller is payer account 111111111111 (organizations
    describe-organization MasterAccountId matches)
  - [PASS] CUR bucket prod-cur-bucket exists in us-east-1 with
    versioning on, BlockPublicAccess on
  - [PASS] CUR bucket policy grants billingreports.amazonaws.com WRITE
    with aws:SourceAccount=111111111111
  - [PASS] CUR bucket policy grants athena.amazonaws.com READ with
    aws:SourceAccount=111111111111
  - [PASS] Glue database prod_cur will be created (does not exist)
  - [PASS] Athena workgroup finops-cur will be created with
    BytesScannedCutoffPerQuery=1099511627776 (1 TB)
  - [PASS] Athena results bucket prod-athena-results exists with KMS SSE
IAC_TEMPLATE:
  AWSTemplateFormatVersion: '2010-09-09'
  Resources:
    CURReport:
      Type: AWS::CUR::ReportDefinition
      Properties:
        ReportName: prod-cur-hourly
        TimeUnit: HOURLY
        Format: Parquet
        Compression: Parquet
        AdditionalSchemaElements: [Resources]
        S3Bucket: prod-cur-bucket
        S3Prefix: cur/prod-cur-hourly/
        S3Region: us-east-1
        ReportVersioning: CREATE_NEW
        RefreshClosedReports: true
        ReportPublishingPreferences: { Hourly: true }
    CURDatabase:
      Type: AWS::Glue::Database
      Properties:
        DatabaseInput: { Name: prod_cur }
        CatalogId: !Ref AWS::AccountId
    CURTable:
      Type: AWS::Glue::Table
      Properties:
        DatabaseName: !Ref CURDatabase
        TableInput:
          Name: cur_hourly
          PartitionKeys:
            - { Name: year, Type: string }
            - { Name: month, Type: string }
            - { Name: day, Type: string }
          TableProperties:
            projection.enabled: "true"
            projection.day.type: date
            projection.day.range: "2024/01/01,NOW"
            projection.day.format: "yyyy/MM/dd"
            projection.day.interval: "1"
            projection.day.interval.unit: DAYS
            projection.month.type: date
            projection.month.range: "2024/01,NOW"
            projection.month.format: "yyyy/MM"
            projection.year.type: integer
            projection.year.range: "2024,2999"
            storage.location.template: "s3://prod-cur-bucket/cur/prod-cur-hourly/year=$${year}/month=$${month}/day=$${day}"
    FinOpsWorkgroup:
      Type: AWS::Athena::WorkGroup
      Properties:
        Name: finops-cur
        State: ENABLED
        WorkGroupConfiguration:
          EnforceWorkgroupConfiguration: true
          BytesScannedCutoffPerQuery: 1099511627776
          ResultConfiguration:
            OutputLocation: s3://prod-athena-results/queries/
            EncryptionConfiguration:
              EncryptionOption: SSE_KMS
              KmsKey: arn:aws:kms:us-east-1:111111111111:key/prod-athena-key
          EngineVersion:
            SelectedEngineVersion: Athena engine version 3
    TopSpendersQuery:
      Type: AWS::Athena::NamedQuery
      Properties:
        Name: top_spenders_by_service
        WorkGroup: !Ref FinOpsWorkgroup
        Database: !Ref CURDatabase
        QueryString: |
          SELECT product_servicename AS service,
                 SUM(lineitem_unblendedcost) AS cost
          FROM cur_hourly
          WHERE day BETWEEN date_format(date_trunc('month', current_date), 'yyyy/MM/dd')
                        AND date_format(current_date, 'yyyy/MM/dd')
          GROUP BY product_servicename
          ORDER BY cost DESC LIMIT 20;
MANUAL_GAPS: (none)
NOTES:
  - First CUR delivery arrives within 24 hours (hourly granularity).
  - Resource-level granularity requires hourly CUR + AdditionalSchemaElements=[Resources].
  - Athena queries MUST include a partition predicate on day/month/year
    to avoid full-table scans (1TB DSL will block the worst offenders).
  - Use the daily top-spenders Lambda (part of this template) to emit
    the top-10 services to the #finops Slack channel.
  - Apply via: aws cloudformation deploy --template-file cur-stack.yaml \
      --stack-name prod-cur-automation --capabilities CAPABILITY_IAM
```

## Contrast — MANUAL_STEP_REQUIRED (linked account caller)

```text
OPERATION: create
VERDICT: MANUAL_STEP_REQUIRED
TARGET: linked-account-cur
REQUIREMENTS:
  - [FAIL] Caller is linked account 222222222222, NOT the payer
    account 111111111111. CUR visibility is payer-only — a CUR created
    by this account covers only its own usage, not the organization's.
  - [PASS] S3 bucket exists in this account's region
  - [PASS] Glue database does not exist (will be created)
PIPELINE_TEMPLATE: (held in draft — apply after closing the gap below)
MANUAL_GAPS:
  - GAP: CUR is being created from a linked account. Organization-wide
    CUR requires the payer account to create the report.
    REMEDIATION:
      # In the payer account (111111111111):
      aws cur put-report-definition \
        --report-definition file://cur-definition.json \
        --profile payer-profile

      # Create an IAM role in the payer that lets the linked account
      # query CUR via Athena in the payer's Glue catalog:
      aws iam create-role \
        --role-name LinkedAccountCURReader \
        --assume-role-policy-document file://trust-policy.json \
        --profile payer-profile
    REASON: The CUR API is restricted to the payer account. Cross-account
      Athena access requires an IAM role in the payer that the linked
      account assumes, plus a Glue catalog resource policy grant.
NOTES:
  - If the goal is organization-wide FinOps, run this skill from the
    payer account.
  - If the goal is single-account FinOps, proceed but document that
    only this account's usage is captured.
```

## What the skill caught that a generic assistant misses

1. **Payer-only CUR creation.** A generic assistant writes the CUR
   template without checking the caller. The skill verifies the caller
   is the payer and emits MANUAL_STEP_REQUIRED with the exact cross-
   account IAM role snippet.

2. **Hourly granularity for resource-level.** A generic assistant
   defaults to daily CUR (cheaper, smaller). The skill knows that
   resource-level requires hourly CUR with `AdditionalSchemaElements:
   [Resources]` and emits accordingly.

3. **Partition projection.** A generic assistant omits the projection
   TBLPROPERTIES — the table works for a few months, then silently
   stops returning data past 20k partitions. The skill always emits
   projection properties.

4. **Non-primary Athena workgroup with DSL.** A generic assistant uses
   the `primary` workgroup (no DSL). The skill creates a non-primary
   workgroup with `BytesScannedCutoffPerQuery=1TB` to prevent bill
   shock from unfiltered queries.

5. **Confused-deputy bucket policy.** A generic assistant emits a
   bucket policy with `Principal: {Service: athena.amazonaws.com}`
   but no `aws:SourceAccount` condition. The skill always emits the
   condition.

6. **Athena engine version 3.** A generic assistant omits
   `EngineVersion: Athena engine version 3`. Without it, partition
   projection with `NOW` as the range end silently fails on engine
   version 2. The skill always emits the engine version.

7. **CONFIRM gate.** A generic assistant auto-executes
   `put-report-definition`. The skill emits CONFIRM and waits — the
   CUR API is idempotent but the bucket policy changes have blast
   radius.

## Slash-command invocation

```
/aws:automate-cur-automation
```

Or via the orchestrator:

```
/aws:pipeline
You: "set up CUR with Athena for prod-cur-automation"
```

The orchestrator emits
`[Phase: Automate | Skills routed: cur-automation-automator]` and hands
off to this skill for the VERDICT.

## CLI routing

```bash
node cli/bin/cli.js route "set up CUR with Athena for payer account"
# [Phase: Automate | Skills routed: cur-automation-automator]
```

## Live-account follow-up (optional, requires AWS CLI)

After the stack is applied:

```bash
# Verify the CUR definition was created
aws cur describe-report-definitions \
  --report-name prod-cur-hourly \
  --profile default

# Wait 24 hours, then verify first delivery
aws s3 ls s3://prod-cur-bucket/cur/prod-cur-hourly/ \
  --recursive --human-readable \
  --profile default | head -20

# Smoke-test the Athena query
aws athena start-query-execution \
  --query-string "SELECT COUNT(*) FROM cur_hourly WHERE day = date_format(current_date, 'yyyy/MM/dd')" \
  --work-group finops-cur \
  --query-execution-context Database=prod_cur \
  --profile default

# Verify the workgroup DSL is enforced
aws athena get-work-group \
  --work-group finops-cur \
  --profile default \
  --query 'WorkGroup.Configuration.BytesScannedCutoffPerQuery'
```
