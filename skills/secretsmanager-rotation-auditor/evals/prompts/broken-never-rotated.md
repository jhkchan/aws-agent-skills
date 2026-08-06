# Eval prompt: broken-never-rotated

Audit the following Secrets Manager secret for rotation health and credential
hygiene. Emit the standard VERDICT block (SECRET, VERDICT, REASON, RISK,
REMEDIATION).

Current date: 2026-08-04

Secret name: legacy-oracle-credentials
Secret type: AWS::RDS::DBInstance
Description: Oracle credentials for legacy reporting database
RotationEnabled: true
RotationLambdaARN: arn:aws:lambda:us-east-1:123456789012:function:OracleRotationLambda
RotationRules:
  AutomaticallyAfterDays: 30
LastRotatedDate: (null — never rotated)
LastChangedDate: 2026-05-05T00:00:00Z
CreatedDate: 2026-05-05T00:00:00Z
DeletedDate: (none)
KmsKeyId: default (aws/secretsmanager)
VersionIdsToStages:
  v1: ["AWSCURRENT"]
Lambda:
  State: Active
  Role: arn:aws:iam::123456789012:role/service-role/OracleRotationLambda
  RolePolicies: [SecretsManagerRotation, AWSLambdaVPCAccessExecutionRole]
  Timeout: 60
  VpcConfig:
    SubnetIds: [subnet-eee555, subnet-fff666]
    SecurityGroupIds: [sg-oracle-lambda]
  LastInvocation:
    Status: ERROR
    ErrorCode: ResourceNotFoundException
    ErrorMessage: DBInstance not found: oracle-legacy-prod (the RDS instance was deleted on 2026-06-15)
