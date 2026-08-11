# Eval prompt: sbom-export-completed

Plan the following Inspector SBOM export and emit the standard
VERDICT block (post-verification form).

Operation: export-sbom (post-verification)
Account: 111111111111
Region: us-east-1
Report format: CYCLONEDX_1_5
S3 destination: s3://inspector-sbom-prod/sbom/us-east-1/
KMS key: arn:aws:kms:us-east-1:111111111111:key/abcd1234
Resource filter: AWS_ECR_CONTAINER_IMAGE

```json
{
  "SbomPreCheck": {
    "s3api.get-bucket-policy.inspector-sbom-prod": {
      "grants": ["s3:PutObject to inspector2.amazonaws.com"]
    },
    "kms.describe-key.abcd1234": {
      "KeyState": "Enabled",
      "policy_grants": ["kms:GenerateDataKey to inspector2.amazonaws.com"]
    },
    "list-sbom-export": {
      "concurrent_for_scope": false
    }
  },
  "SbomExecution": {
    "executed_cli": "aws inspector2 start-sbom-export --report-format CYCLONEDX_1_5 --s3-destination ... --resource-filter-criteria ...",
    "returned_report_id": "0a1b2c3d-4e5f-6071-8290-abcd1234ef56"
  },
  "SbomPostVerify": {
    "list-sbom-export.0a1b2c3d-...": {
      "status": "COMPLETED",
      "destinationBucket": "inspector-sbom-prod"
    },
    "s3api.head-object.sbom/us-east-1/0a1b2c3d-...json": {
      "ContentLength": 482310
    }
  }
}
```
