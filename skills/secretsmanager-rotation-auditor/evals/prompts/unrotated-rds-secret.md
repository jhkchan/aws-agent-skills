# Eval prompt: unrotated-rds-secret

Audit the following Secrets Manager secret for rotation health and credential
hygiene. Emit the standard VERDICT block (SECRET, VERDICT, REASON, RISK,
REMEDIATION).

Secret name: prod-rds-postgres-credentials
Secret type: AWS::RDS::DBInstance
Description: Primary PostgreSQL credentials for the production orders database
RotationEnabled: false
RotationLambdaARN: (none)
RotationRules:
  AutomaticallyAfterDays: (none)
LastRotatedDate: (never — secret was created 180 days ago)
LastChangedDate: 2026-02-05T00:00:00Z
DeletedDate: (none)
KmsKeyId: default (aws/secretsmanager)
VersionIdsToStages:
  v1: ["AWSCURRENT"]
