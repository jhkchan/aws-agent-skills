# Eval prompt: alternating-users-strategy-conflict

Diagnose the Secrets Manager rotation failure for the following secret.
Walk the symptom-driven diagnostic tree and emit the standard diagnostic
block (TARGET, VERDICT, REASON, LAYER, EVIDENCE, REMEDIATION).

Symptom: secret `prod/db/alternating-users-strategy-conflict` started
failing after a rotation Lambda re-deploy last week. The Lambda logs
`permission denied; cannot modify own password` in the `setSecret`
step. The rotation role and DB privileges worked correctly before the
re-deploy.

```text
SecretId: prod/db/alternating-users-strategy-conflict
RotationEnabled: true
RotationLambdaARN: arn:aws:lambda:us-east-1:111111111111:function:SecretsManagerRotation-alternating-users-strategy-conflict
RotationRules: {ScheduleExpression: 'rate(1d)'}
LastRotatedDate: 2026-07-29T03:17:22Z
VersionIdsToStages: {"v5": ["AWSCURRENT"], "v4": ["AWSPREVIOUS"],
                      "v6": ["AWSPENDING"]}

Rotation Lambda configuration:
  Description: "SecretsManagerRDSMySQLRotationSingleUser"
  Handler: lambda_function.lambda_handler
  Environment.Variables:
    SECRETS_MANAGER_SECRET_ID: prod/db/alternating-users-strategy-conflict
    SECRETS_MANAGER_MASTER_ID: prod/db/alternating-users-strategy-conflict-master
    ROTATION_STRATEGY: SINGLE_USER
  LastModified: 2026-07-28 (re-deployed 8 days ago)

Prior rotation Lambda (replaced):
  Description: "SecretsManagerRDSMySQLRotationMultiUser"
  ROTATION_STRATEGY: ALTERNATING_USERS

Secret value (non-sensitive fields):
  engine: mysql
  host: prod-db.cxyz.us-east-1.rds.amazonaws.com
  port: 3306
  dbname: payments
  username: app_user

Master Secret value (non-sensitive fields):
  engine: mysql
  username: rotation_master
  (verified SUPERUSER privilege)

Recent rotation Lambda log pattern:
  [INFO]  createSecret: staging new password as AWSPENDING v6
  [INFO]  setSecret: connecting as app_user to rotate own password
  [ERROR] ERROR 1227 (42000): Access denied; you need (at least
          one of) the SUPER privilege(s) for this operation.
          Statement: ALTER USER 'app_user'@'%' IDENTIFIED BY '<new>'

Database context: app_user has only the application-level grants
  (SELECT, INSERT, UPDATE on payments.*); no SUPER, no CREATE USER.

Rotation role permissions (all verified ALLOWED):
  secretsmanager:GetSecretValue on rotating + Master secret
  secretsmanager:PutSecretValue
  kms:Decrypt on alias/aws/secretsmanager (not required)
  VPC config correctly attached to DB subnets
```

The Single User template (`SecretsManagerRDSMySQLRotationSingleUser`)
authenticates as the rotating user (`app_user`) and runs `ALTER USER
'app_user'@'%' IDENTIFIED BY`. MySQL rejects a user modifying its own
password without the `SUPER` privilege. The prior Lambda used the
Alternating Users template (`SecretsManagerRDSMySQLRotationMultiUser`),
which authenticates as the Master Secret's `rotation_master` user and
creates a clone — that worked because `rotation_master` has SUPER.

This is a template/strategy mismatch (`STRATEGY_CONFLICT`), not a DB
privilege regression (`SUPERUSER_INSUFFICIENT`) — the Master Secret's
user has SUPER, but the Single User template does not use the Master
Secret at all. The fix is to re-deploy the rotation Lambda with the
Multi User (Alternating) template family.
