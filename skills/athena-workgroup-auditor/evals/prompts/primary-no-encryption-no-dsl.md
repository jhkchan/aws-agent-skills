# Eval prompt: primary-no-encryption-no-dsl

Audit the following Athena workgroup configuration for security exposure.
Emit the standard VERDICT block (WORKGROUP, VERDICT, REASON, FINDINGS,
REMEDIATION).

Workgroup name: primary
Workgroup metadata:
  State: ENABLED
  Description: Auto-created default Athena workgroup.

Configuration:

```json
{
  "EnforceWorkGroupConfiguration": false,
  "ResultConfiguration": {
    "OutputLocation": ""
  },
  "BytesScannedCutoffPerQuery": null,
  "PublishCloudWatchMetricsEnabled": false,
  "EngineVersion": {
    "SelectedEngineVersion": "Athena engine version 3"
  }
}
```

Named queries: none
