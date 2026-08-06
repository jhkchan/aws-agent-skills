# Eval prompt: enforce-off-configs-advisory

Audit the following Athena workgroup configuration for security exposure.
Emit the standard VERDICT block (WORKGROUP, VERDICT, REASON, FINDINGS,
REMEDIATION).

Workgroup name: etl-enforce-off-configs-advisory
Workgroup metadata:
  State: ENABLED
  Description: ETL workgroup — controls present but not enforced.

Configuration:

```json
{
  "EnforceWorkGroupConfiguration": false,
  "ResultConfiguration": {
    "OutputLocation": "s3://athena-results-111111111111-us-east-1/etl/",
    "EncryptionConfiguration": {
      "EncryptionOption": "SSE_KMS",
      "KmsKey": "arn:aws:kms:us-east-1:111111111111:key/def-456"
    }
  },
  "BytesScannedCutoffPerQuery": 1099511627776,
  "PublishCloudWatchMetricsEnabled": true,
  "EngineVersion": {
    "SelectedEngineVersion": "Athena engine version 3"
  }
}
```

Named queries: none
