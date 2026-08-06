# Eval prompt: no-encryption-dsl-set

Audit the following Athena workgroup configuration for security exposure.
Emit the standard VERDICT block (WORKGROUP, VERDICT, REASON, FINDINGS,
REMEDIATION).

Workgroup name: adhoc-no-encryption-dsl-set
Workgroup metadata:
  State: ENABLED
  Description: Ad-hoc querying workgroup for data scientists.

Configuration:

```json
{
  "EnforceWorkGroupConfiguration": true,
  "ResultConfiguration": {
    "OutputLocation": "s3://athena-results-111111111111-us-east-1/adhoc/"
  },
  "BytesScannedCutoffPerQuery": 1099511627776,
  "PublishCloudWatchMetricsEnabled": true,
  "EngineVersion": {
    "SelectedEngineVersion": "Athena engine version 3"
  }
}
```

Named queries: none
