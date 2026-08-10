# Eval prompt: kms-reencrypt-job-blocked-key-policy

Plan the following S3 Batch Operations bulk KMS re-encrypt job and
emit the standard VERDICT block (OPERATION, VERDICT, TARGET,
PRE_CHECKS, STEPS, POST_VERIFY, NOTES).

Operation: create-job
Operation type: Copy (in-place re-encrypt with new SSE-KMS key)
Source/destination: prod-data (same bucket)
Manifest: s3://prod-inventory/2026-08-01/manifest.json (12.4M objects)
Report bucket: prod-batch-reports (us-east-1)
Role: arn:aws:iam::111111111111:role/S3BatchOpsRole
RequestsPerSecond: 1000
New KMS key: arn:aws:kms:us-east-1:111111111111:key/new-key

```json
{
  "RoleIdentityPolicy": [
    "kms:Decrypt on arn:aws:kms:us-east-1:111111111111:key/old-key",
    "kms:Encrypt on arn:aws:kms:us-east-1:111111111111:key/new-key"
  ],
  "NewKmsKeyPolicy": {
    "Statements": [
      {
        "Effect": "Allow",
        "Principal": {"AWS": "arn:aws:iam::111111111111:root"},
        "Action": "kms:*",
        "Resource": "*"
      }
    ],
    "MissingGrant": "The role ARN arn:aws:iam::111111111111:role/S3BatchOpsRole is not explicitly granted kms:Encrypt via the key policy's service-linked statement. Batch Operations assumes the role and the key policy grant must include the role ARN explicitly for cross-service access."
  },
  "CallerPermissions": {
    "s3control:CreateJob": true,
    "iam:PassRole": "arn:aws:iam::111111111111:role/S3BatchOpsRole"
  },
  "Manifest": {
    "Format": "S3InventoryReport",
    "ObjectArn": "arn:aws:s3:::prod-inventory/2026-08-01/manifest.json"
  }
}
```
