# Eval prompt: create-copy-job-inventory-manifest-ready

Plan the following S3 Batch Operations copy job and emit the standard
VERDICT block (OPERATION, VERDICT, TARGET, PRE_CHECKS, STEPS,
POST_VERIFY, NOTES).

Operation: create-job
Operation type: Copy (in-place re-encrypt with new SSE-KMS key)
Manifest: s3://prod-inventory/2026-08-01/manifest.json (S3 inventory, versioned V2)
Source bucket: prod-data (SSE-KMS with old-key)
Destination: same bucket (in-place re-encrypt), new SSE-KMS key
Report bucket: prod-batch-reports (us-east-1)
Role: arn:aws:iam::111111111111:role/S3BatchOpsRole
RequestsPerSecond: 500
Priority: 50
Estimated object count: 12,400,000

```json
{
  "CallerPermissions": {
    "s3control:CreateJob": true,
    "iam:PassRole": "arn:aws:iam::111111111111:role/S3BatchOpsRole"
  },
  "RoleTrust": {
    "AllowedPrincipal": "batchoperations.amazonaws.com",
    "Action": "sts:AssumeRole"
  },
  "RolePolicies": [
    "s3:GetObject on prod-data/*",
    "s3:PutObject on prod-data/*",
    "s3:GetObject on prod-inventory/manifests/*",
    "s3:PutObject on prod-batch-reports/*",
    "kms:Decrypt on arn:aws:kms:us-east-1:111111111111:key/old-key",
    "kms:Encrypt on arn:aws:kms:us-east-1:111111111111:key/new-key"
  ],
  "NewKmsKeyPolicy": {
    "GrantsRoleEncrypt": true,
    "KeyId": "arn:aws:kms:us-east-1:111111111111:key/new-key"
  },
  "Manifest": {
    "Format": "S3InventoryReport",
    "Fields": ["Bucket", "Key", "VersionId"],
    "ObjectArn": "arn:aws:s3:::prod-inventory/2026-08-01/manifest.json",
    "ETag": "present"
  },
  "ReportBucket": {"Name": "prod-batch-reports", "Region": "us-east-1"}
}
```
