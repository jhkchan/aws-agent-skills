# Eval prompt: greenfield-cur-athena-automated

Design a greenfield CUR + Athena automation stack for a payer account
and emit the standard VERDICT block (OPERATION, VERDICT, TARGET,
REQUIREMENTS, IAC_TEMPLATE, MANUAL_GAPS, NOTES).

Operation: create
Stack name: prod-cur-automation
Caller: payer account 111111111111
CUR bucket: prod-cur-bucket (us-east-1, versioning on,
  BlockPublicAccess on, policy grants billingreports.amazonaws.com +
  athena.amazonaws.com with aws:SourceAccount=111111111111)
Granularity: HOURLY
Resource-level: yes (AdditionalSchemaElements: Resources)
Format: Parquet
ReportVersioning: CREATE_NEW
Glue database: prod_cur (does not exist, will be created)
Athena workgroup: finops-cur (does not exist, will be created) with
  EnforceWorkgroupConfiguration=true,
  BytesScannedCutoffPerQuery=1TB
Athena results bucket: prod-athena-results (KMS SSE)
Query automation: top_spenders_by_service daily
Template format: CloudFormation

```json
{
  "RequirementChecks": {
    "organizations.describe-organization": {
      "MasterAccountId": "111111111111"
    },
    "sts.get-caller-identity": {
      "Account": "111111111111"
    },
    "cur.describe-report-definitions": [],
    "s3api.get-bucket-location.prod-cur-bucket": {
      "LocationConstraint": "us-east-1"
    },
    "s3api.get-bucket-versioning.prod-cur-bucket": {
      "Status": "Enabled"
    },
    "s3api.get-bucket-policy.prod-cur-bucket": {
      "Statement[0].Principal.Service": "billingreports.amazonaws.com",
      "Statement[1].Principal.Service": "athena.amazonaws.com"
    },
    "glue.get-database.prod_cur": {
      "Status": "EntityNotFoundException"
    },
    "athena.list-work-groups": ["primary"],
    "kms.describe-key.prod-athena-key": {
      "Enabled": true
    }
  }
}
```
