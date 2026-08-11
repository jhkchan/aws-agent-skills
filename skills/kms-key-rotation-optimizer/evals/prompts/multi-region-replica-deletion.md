# Eval prompt: multi-region-replica-deletion

Optimise the following multi-region KMS key for cost and lifecycle.
Walk the multi-region key decision framework and emit the standard
optimization block (TARGET, VERDICT, REASON, RECOMMENDATION,
ESTIMATED_SAVINGS, REMEDIATION_STEPS).

KeyId: arn:aws:kms:us-east-1:123456789012:key/multi-region-replica-deletion
Alias: alias/global-data-encryption
KeyState: Enabled
KeyManager: CUSTOMER
KeySpec: SYMMETRIC_DEFAULT
RotationStatus: Enabled (annual)
MultiRegion: True
  - Primary: us-east-1
  - Replicas:
    - eu-west-1: 12,000 Decrypt calls/30 days (active)
    - ap-southeast-1: 0 calls/30 days (unused)
    - sa-east-1: 0 calls/30 days (unused)
Grants: 4 active (all current)
Region: us-east-1

CloudTrail (last 30 days):
  - us-east-1: Decrypt 50,000, Encrypt 8,000, GenerateDataKey 2,000
  - eu-west-1: Decrypt 12,000, Encrypt 1,500, GenerateDataKey 300
  - ap-southeast-1: 0 calls
  - sa-east-1: 0 calls

Resource associations:
  - S3 (us-east-1): 5 buckets
  - S3 (eu-west-1): 2 buckets
  - S3 (ap-southeast-1): 0 buckets
  - S3 (sa-east-1): 0 buckets
