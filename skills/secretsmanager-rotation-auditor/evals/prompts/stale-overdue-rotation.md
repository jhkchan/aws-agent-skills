# Eval prompt: stale-overdue-rotation

Audit the following Secrets Manager secret for rotation health and credential
hygiene. Emit the standard VERDICT block (SECRET, VERDICT, REASON, RISK,
REMEDIATION).

Current date: 2026-08-04

Secret name: documentdb-cluster-credentials
Secret type: AWS::DocDB::DBCluster
Description: DocumentDB credentials for content metadata cluster
RotationEnabled: true
RotationLambdaARN: arn:aws:lambda:us-east-1:123456789012:function:DocDBRotationLambda
RotationRules:
  AutomaticallyAfterDays: 30
LastRotatedDate: 2026-05-01T02:00:00Z
Days since last rotation: 95
LastChangedDate: 2026-05-01T02:00:00Z
DeletedDate: (none)
KmsKeyId: default (aws/secretsmanager)
VersionIdsToStages:
  v5: ["AWSCURRENT"]
  v4: ["AWSPREVIOUS"]
Lambda:
  State: Active
  Role: arn:aws:iam::123456789012:role/service-role/DocDBRotationLambda
  RolePolicies: [SecretsManagerRotation, AWSLambdaVPCAccessExecutionRole]
  Timeout: 30
  VpcConfig:
    SubnetIds: [subnet-ccc333, subnet-ddd444]
    SecurityGroupIds: [sg-docdb-lambda]
  LastInvocation:
    Status: SUCCESS
    Timestamp: 2026-05-01T02:00:00Z
