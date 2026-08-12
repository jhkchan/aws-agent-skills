# Eval prompt: rotation-lambda-vpc-timeout

Diagnose the Secrets Manager rotation failure for the following secret.
Walk the symptom-driven diagnostic tree and emit the standard diagnostic
block (TARGET, VERDICT, REASON, LAYER, EVIDENCE, REMEDIATION).

Symptom: secret `prod/db/rotation-lambda-vpc-timeout` has not rotated
in 8 days. The rotation Lambda logs `Could not connect to database at
host prod-db.cluster-cxyz.us-east-1.rds.amazonaws.com port 5432`
followed by `Task timed out after 15.00 seconds` on every rotation
attempt.

```text
SecretId: prod/db/rotation-lambda-vpc-timeout
RotationEnabled: true
RotationLambdaARN: arn:aws:lambda:us-east-1:111111111111:function:SecretsManagerRotation-rotation-lambda-vpc-timeout
RotationRules: {ScheduleExpression: 'rate(1d)'}
LastRotatedDate: 2026-07-28T03:17:22Z
KmsKeyId: alias/aws/secretsmanager
VersionIdsToStages: {"v1": ["AWSCURRENT"], "v2": ["AWSPENDING"]}

Rotation Lambda configuration:
  Timeout: 15
  MemorySize: 256
  Runtime: python3.12
  Handler: lambda_function.lambda_handler
  VpcConfig: (none — VpcId is empty)
  Role: arn:aws:iam::111111111111:role/SecretsManagerRotation-role
  Environment.Variables:
    SECRETS_MANAGER_SECRET_ID: prod/db/rotation-lambda-vpc-timeout
    SECRETS_MANAGER_MASTER_ID: prod/db/rotation-lambda-vpc-timeout-master

Database context:
  Engine: aurora-postgresql
  Cluster endpoint: prod-db.cluster-cxyz.us-east-1.rds.amazonaws.com
  Port: 5432
  Subnet: subnet-private-a (10.0.10.0/24), route table local-only
  Security Group sg-db: ingress 5432 from sg-app (no sg-lambda-rotation)

Recent rotation Lambda log pattern (last 8 attempts):
  [INFO]  createSecret: staging new password as AWSPENDING v3
  [INFO]  setSecret: attempting connection to host
          prod-db.cluster-cxyz.us-east-1.rds.amazonaws.com port 5432
  [ERROR] Could not connect to database at host
          prod-db.cluster-cxyz.us-east-1.rds.amazonaws.com port 5432
  Task timed out after 15.00 seconds

Rotation role simulate-principal-policy:
  secretsmanager:GetSecretValue on the secret: ALLOWED
  secretsmanager:PutSecretValue on the secret: ALLOWED
  kms:Decrypt on alias/aws/secretsmanager: not required (AWS-managed)
```

The Lambda is not VPC-attached but the database is in a private
subnet. Lambda functions without VPC attachment cannot reach private
RDS endpoints — the Lambda's outbound TCP to port 5432 has no route.
Distinguish this (DB unreachable) from ROTATION_LAMBDA_TIMEOUT
(Timeout config too low). The configured Timeout is 15s, which is
adequate for a reachable DB; the failure is the network path, not the
timeout value.
