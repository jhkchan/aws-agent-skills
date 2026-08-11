# Eval prompt: already-optimal-key

Optimise the following KMS key for cost and lifecycle. Walk the full
seven-dimension decision framework and emit the standard optimization
block (TARGET, VERDICT, REASON, RECOMMENDATION, ESTIMATED_SAVINGS,
REMEDIATION_STEPS).

KeyId: arn:aws:kms:us-east-1:123456789012:key/already-optimal-key
Alias: alias/production-data-encryption
KeyState: Enabled
KeyManager: CUSTOMER
KeySpec: SYMMETRIC_DEFAULT
RotationStatus: Enabled (annual, last rotated 3 months ago)
Grants: 3 active (all current, all recently used in CloudTrail)
MultiRegion: False
Region: us-east-1

CloudTrail (last 30 days):
  - Decrypt: 2,500,000 calls
  - Encrypt: 350,000 calls
  - GenerateDataKey: 80,000 calls

Resource associations:
  - S3 bucket default encryption: 8 buckets reference this key
  - EBS volumes: None
  - RDS instances: None
