# Eval prompt: lifecycle-verified-completed

Post-verification of a completed S3 lifecycle configuration apply.
Emit the standard VERDICT block (post-verification form).

Operation: configure-lifecycle (post-verification after apply)
Bucket: prod-logs-bucket
Region: us-east-1
Account: 111111111111

```json
{
  "LifecyclePutResult": {
    "CommandExecuted": "aws s3api put-bucket-lifecycle-configuration --bucket prod-logs-bucket --lifecycle-configuration file:///tmp/prod-logs-bucket-merged.json",
    "HttpResult": 200
  },
  "PostApplyChecks": {
    "GetLifecycleConfiguration_48h": {
      "Rules": [
        {"ID": "current-version-tier-to-ia", "Status": "Enabled"},
        {"ID": "current-version-expire-365d", "Status": "Enabled"},
        {"ID": "abort-multipart-7d", "Status": "Enabled"},
        {
          "ID": "version-cleanup-3-rule",
          "Status": "Enabled",
          "NoncurrentVersionTransition": [
            {"NoncurrentDays": 30, "StorageClass": "STANDARD_IA"},
            {"NoncurrentDays": 90, "StorageClass": "GLACIER_IR"}
          ],
          "NoncurrentVersionExpiration": {"NewerNoncurrentVersions": 3}
        }
      ]
    },
    "StorageLens_48h": {
      "NoncurrentVersionCount_Before": 540000,
      "NoncurrentVersionCount_After": 412000,
      "NoncurrentVersionCount_Delta": "-24%",
      "NoncurrentVersionStorageBytes_Before": 13500000000000,
      "NoncurrentVersionStorageBytes_After": 9800000000000,
      "NoncurrentVersionStorageBytes_Delta": "-27%"
    },
    "CostExplorer_3d": {
      "Trend": "S3 cost for prod-logs-bucket trending down ~$80/week"
    }
  },
  "OriginalRulesPreserved": [
    "current-version-tier-to-ia",
    "current-version-expire-365d",
    "abort-multipart-7d"
  ]
}
```
