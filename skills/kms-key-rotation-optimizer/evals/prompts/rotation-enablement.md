# Eval prompt: rotation-enablement

Optimise the following KMS key for cost and lifecycle. Walk the rotation
and grant decision framework and emit the standard optimization block
(TARGET, VERDICT, REASON, RECOMMENDATION, ESTIMATED_SAVINGS,
REMEDIATION_STEPS).

KeyId: arn:aws:kms:us-east-1:123456789012:key/rotation-enablement
Alias: alias/secrets-encryption
KeyState: Enabled
KeyManager: CUSTOMER
KeySpec: SYMMETRIC_DEFAULT
RotationStatus: Disabled (no regulatory prohibition)
Grants: 5 total
  - 3 active grants (current IAM roles)
  - 2 expired grants (grantee principals deleted 30+ days ago)
MultiRegion: False
Region: us-east-1

CloudTrail (last 30 days):
  - Decrypt: 45,000 calls
  - Encrypt: 3,000 calls
  - GenerateDataKey: 1,200 calls

Resource associations:
  - Secrets Manager: 15 secrets reference this key
  - S3: None
  - EBS: None
