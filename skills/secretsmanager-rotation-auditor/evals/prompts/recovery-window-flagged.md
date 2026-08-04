# Eval prompt: recovery-window-flagged

Audit the following Secrets Manager secret for rotation health and credential
hygiene. Emit the standard VERDICT block (SECRET, VERDICT, REASON, RISK,
REMEDIATION).

Current date: 2026-08-04

Secret name: payment-gateway-api-token
Secret type: Other
Description: Stripe API key for payment processing
RotationEnabled: false
RotationLambdaARN: (none)
RotationRules:
  AutomaticallyAfterDays: (none)
LastRotatedDate: (never)
LastChangedDate: 2026-01-10T00:00:00Z
DeletedDate: 2026-08-12T00:00:00Z
RecoveryWindowInDays: 30
KmsKeyId: default (aws/secretsmanager)
VersionIdsToStages:
  v1: ["AWSCURRENT"]
