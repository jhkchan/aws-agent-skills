# Eval prompt: ok-healthy-rotation

Audit the following Secrets Manager secret for rotation health and credential
hygiene. Emit the standard VERDICT block (SECRET, VERDICT, REASON, RISK,
REMEDIATION).

Current date: 2026-08-04

Secret name: staging-rds-mysql-credentials
Secret type: AWS::RDS::DBInstance
Description: MySQL credentials for staging environment
RotationEnabled: true
RotationLambdaARN: arn:aws:lambda:us-east-1:123456789012:function:SecretsManagerRotation-MySQL
RotationRules:
  AutomaticallyAfterDays: 30
LastRotatedDate: 2026-07-28T03:15:00Z
LastChangedDate: 2026-07-28T03:15:00Z
DeletedDate: (none)
KmsKeyId: default (aws/secretsmanager)
VersionIdsToStages:
  v4: ["AWSCURRENT"]
  v3: ["AWSPREVIOUS"]
Lambda:
  State: Active
  Role: arn:aws:iam::123456789012:role/service-role/SecretsManagerRotation-MySQL
  RolePolicies: [SecretsManagerRotation, AWSLambdaVPCAccessExecutionRole]
  Timeout: 30
  VpcConfig:
    SubnetIds: [subnet-aaa111, subnet-bbb222]
    SecurityGroupIds: [sg-rdslambda]
  LastInvocation:
    Status: SUCCESS
    Timestamp: 2026-07-28T03:15:00Z
