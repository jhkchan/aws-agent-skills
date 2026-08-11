# Eval prompt: orphaned-key-cleanup

Optimise the following KMS key for cost and lifecycle. Walk the key
inventory and grant decision framework and emit the standard
optimization block (TARGET, VERDICT, REASON, RECOMMENDATION,
ESTIMATED_SAVINGS, REMEDIATION_STEPS).

KeyId: arn:aws:kms:us-east-1:123456789012:key/orphaned-key-cleanup
Alias: alias/legacy-app-encryption
KeyState: Enabled
KeyManager: CUSTOMER
KeySpec: SYMMETRIC_DEFAULT
RotationStatus: Disabled
Grants: 3 active (all expired, grantee principals deleted)
MultiRegion: False
Region: us-east-1

CloudTrail (last 30 days):
  - Decrypt: 0 calls
  - Encrypt: 0 calls
  - GenerateDataKey: 0 calls

Resource associations:
  - S3 bucket default encryption: None referencing this key
  - EBS volumes: None referencing this key
  - RDS instances: None referencing this key
  - Secrets Manager: None referencing this key
