# Eval prompt: all-clean-ok

Audit the following Athena workgroup configuration for security exposure.
Emit the standard VERDICT block (WORKGROUP, VERDICT, REASON, FINDINGS,
REMEDIATION).

Workgroup name: lakehouse-all-clean-ok
Workgroup metadata:
  State: ENABLED
  Description: Production lakehouse workgroup — fully governed.

Configuration:

```json
{
  "EnforceWorkGroupConfiguration": true,
  "ResultConfiguration": {
    "OutputLocation": "s3://athena-results-111111111111-us-east-1/lakehouse/",
    "EncryptionConfiguration": {
      "EncryptionOption": "SSE_KMS",
      "KmsKey": "arn:aws:kms:us-east-1:111111111111:key/lakehouse-cmk"
    }
  },
  "BytesScannedCutoffPerQuery": 1099511627776,
  "PublishCloudWatchMetricsEnabled": true,
  "EngineVersion": {
    "SelectedEngineVersion": "Athena engine version 3"
  }
}
```

Named queries:

- `NamedQueryId: nq-aaa`
  - Name: top_customers_by_revenue
  - WorkGroup: lakehouse-all-clean-ok
  - QueryString: `SELECT customer_id, SUM(revenue) FROM orders GROUP BY customer_id ORDER BY 2 DESC LIMIT 100`

Named query IAM: `athena:GetNamedQuery` and `athena:StartNamedQuery` are
granted only to `arn:aws:iam::111111111111:role/bi-reader-role` on
`arn:aws:athena:us-east-1:111111111111:workgroup/lakehouse-all-clean-ok`.
No `Principal: "*"` grants. No cross-account grants.

CloudTrail context: A trail in us-east-1 has Athena data events enabled
for `arn:aws:athena:us-east-1:111111111111:workgroup/lakehouse-all-clean-ok`.
