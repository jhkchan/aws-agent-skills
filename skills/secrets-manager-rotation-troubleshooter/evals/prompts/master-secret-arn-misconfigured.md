# Eval prompt: master-secret-arn-misconfigured

Diagnose the Secrets Manager rotation failure for the following secret.
Walk the symptom-driven diagnostic tree and emit the standard diagnostic
block (TARGET, VERDICT, REASON, LAYER, EVIDENCE, REMEDIATION).

Symptom: secret `prod/auth/master-secret-arn-misconfigured` fails
every rotation. The Lambda logs `ResourceNotFoundException: Secrets
Manager can't find the specified secret. ARN:
arn:aws:secretsmanager:us-east-1:111111111111:secret:prod/auth/missing-master-6fXq2L`
in the `createSecret` step. LastRotatedDate is 5 days stale.

```text
SecretId: prod/auth/master-secret-arn-misconfigured
RotationEnabled: true
RotationLambdaARN: arn:aws:lambda:us-east-1:111111111111:function:SecretsManagerRotation-master-secret-arn-misconfigured
RotationRules: {ScheduleExpression: 'rate(1d)'}
LastRotatedDate: 2026-07-31T03:17:22Z

Rotation Lambda environment variables:
  SECRETS_MANAGER_SECRET_ID: prod/auth/master-secret-arn-misconfigured
  SECRETS_MANAGER_MASTER_ID: arn:aws:secretsmanager:us-east-1:111111111111:secret:prod/auth/missing-master-6fXq2L

secretsmanager describe-secret on the configured Master ARN:
  ResourceNotFoundException: Secrets Manager can't find the
  specified secret.

CloudTrail context: a DeleteSecret event for
  prod/auth/missing-master was recorded 7 days ago by the security
  team ("Decommissioned per compliance purge").

Recent rotation Lambda log pattern:
  [INFO]  createSecret: loading Master Secret
          arn:aws:secretsmanager:us-east-1:111111111111:secret:prod/auth/missing-master-6fXq2L
  [ERROR] ResourceNotFoundException: Secrets Manager can't find
          the specified secret.

Rotation role permissions:
  secretsmanager:GetSecretValue on the configured Master ARN:
    ALLOWED in identity policy (but resource does not exist)
  secretsmanager:PutSecretValue on the rotating secret: ALLOWED
```

The rotation Lambda's `SECRETS_MANAGER_MASTER_ID` environment variable
points at a Master Secret that was deleted 7 days ago. The role's IAM
policy grants `GetSecretValue` on the configured ARN, so this is NOT
an IAM (`PERMISSION_ROTATION_ROLE`) issue — the resource itself does
not exist. The fix is to point the env var at a valid Master Secret
ARN, not to edit the role policy.
