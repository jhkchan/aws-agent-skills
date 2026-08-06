# Eval prompt: broken-lambda-deleted

Audit the following Secrets Manager secret for rotation health and credential
hygiene. Emit the standard VERDICT block (SECRET, VERDICT, REASON, RISK,
REMEDIATION).

Current date: 2026-08-04

Secret name: analytics-redshift-credentials
Secret type: AWS::Redshift::Cluster
Description: Redshift credentials for analytics cluster
RotationEnabled: true
RotationLambdaARN: arn:aws:lambda:us-east-1:123456789012:function:RedshiftRotationLambda
RotationRules:
  AutomaticallyAfterDays: 60
LastRotatedDate: 2025-12-15T08:00:00Z
LastChangedDate: 2025-12-15T08:00:00Z
DeletedDate: (none)
KmsKeyId: default (aws/secretsmanager)
VersionIdsToStages:
  v2: ["AWSCURRENT"]
  v1: ["AWSPREVIOUS"]
Lambda:
  State: Deleted (ResourceNotFoundException — function was deleted on 2026-03-01)
  Role: (n/a — function does not exist)
  LastInvocation:
    Status: ERROR
    ErrorCode: ResourceNotFoundException
    ErrorMessage: Function not found: arn:aws:lambda:us-east-1:123456789012:function:RedshiftRotationLambda
