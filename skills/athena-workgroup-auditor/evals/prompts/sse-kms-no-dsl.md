# Eval prompt: sse-kms-no-dsl

Audit the following Athena workgroup configuration for security exposure.
Emit the standard VERDICT block (WORKGROUP, VERDICT, REASON, FINDINGS,
REMEDIATION).

Workgroup name: analytics-sse-kms-no-dsl
Workgroup metadata:
  State: ENABLED
  Description: Analytics workgroup for the BI team.

Configuration:

```json
{
  "EnforceWorkGroupConfiguration": true,
  "ResultConfiguration": {
    "OutputLocation": "s3://athena-results-111111111111-us-east-1/analytics/",
    "EncryptionConfiguration": {
      "EncryptionOption": "SSE_KMS",
      "KmsKey": "arn:aws:kms:us-east-1:111111111111:key/abc-123"
    }
  },
  "BytesScannedCutoffPerQuery": null,
  "PublishCloudWatchMetricsEnabled": true,
  "EngineVersion": {
    "SelectedEngineVersion": "Athena engine version 3"
  }
}
```

Named queries: none
