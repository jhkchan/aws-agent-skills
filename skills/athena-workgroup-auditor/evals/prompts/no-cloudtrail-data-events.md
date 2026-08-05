# Eval prompt: no-cloudtrail-data-events

Audit the following Athena workgroup configuration for security exposure.
Emit the standard VERDICT block (WORKGROUP, VERDICT, REASON, FINDINGS,
REMEDIATION).

Workgroup name: bi-no-cloudtrail-data-events
Workgroup metadata:
  State: ENABLED
  Description: BI workgroup for regulated workloads.

Configuration:

```json
{
  "EnforceWorkGroupConfiguration": true,
  "ResultConfiguration": {
    "OutputLocation": "s3://athena-results-111111111111-us-east-1/bi/",
    "EncryptionConfiguration": {
      "EncryptionOption": "SSE_KMS",
      "KmsKey": "arn:aws:kms:us-east-1:111111111111:key/bi-key"
    }
  },
  "BytesScannedCutoffPerQuery": 5497558138880,
  "PublishCloudWatchMetricsEnabled": true,
  "EngineVersion": {
    "SelectedEngineVersion": "Athena engine version 3"
  }
}
```

Named queries: none

CloudTrail context: No trail in us-east-1 has `AWS::Athena` data events
enabled. Management events are captured (`StartQueryExecution` etc.) but
data events (`GetQueryResults`, `GetQueryExecution` reads) are absent.
