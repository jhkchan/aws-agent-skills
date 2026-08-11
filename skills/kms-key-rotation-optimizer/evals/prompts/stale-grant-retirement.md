# Eval prompt: stale-grant-retirement

Optimise the following KMS key for cost and lifecycle. Walk the grant
optimization decision framework and emit the standard optimization block
(TARGET, VERDICT, REASON, RECOMMENDATION, ESTIMATED_SAVINGS,
REMEDIATION_STEPS).

KeyId: arn:aws:kms:us-east-1:123456789012:key/stale-grant-retirement
Alias: alias/s3-bucket-encryption
KeyState: Enabled
KeyManager: CUSTOMER
KeySpec: SYMMETRIC_DEFAULT
RotationStatus: Enabled (annual)
Grants: 18 total
  - 11 active grants (current IAM roles, recently used in CloudTrail)
  - 7 expired grants (grantee principals deleted 60+ days ago, no CloudTrail usage)
MultiRegion: False
Region: us-east-1

CloudTrail (last 30 days):
  - Decrypt: 850,000 calls
  - Encrypt: 120,000 calls
  - GenerateDataKey: 45,000 calls

Resource associations:
  - S3 bucket default encryption: 3 buckets reference this key
  - EBS volumes: None
  - RDS instances: None
