# Eval prompt: cross-account-secret-access-denied

Diagnose the Secrets Manager rotation failure for the following secret.
Walk the symptom-driven diagnostic tree and emit the standard diagnostic
block (TARGET, VERDICT, REASON, LAYER, EVIDENCE, REMEDIATION).

Symptom: secret `prod/payments/cross-account-secret-access-denied` is
owned by account `111111111111` but rotated by a Lambda in account
`222222222222` (security-tooling account). Every rotation attempt
fails with `AccessDeniedException: User
arn:aws:sts::222222222222:assumed-role/SecretsManagerRotation-role/SecretsManagerRotation-cross-account
is not authorized to perform: secretsmanager:GetSecretValue`.

```text
SecretId: arn:aws:secretsmanager:us-east-1:111111111111:secret:prod/payments/cross-account-secret-access-denied-Ab12Cd
OwningAccount: 111111111111
RotationEnabled: true
RotationLambdaARN: arn:aws:lambda:us-east-1:222222222222:function:SecretsManagerRotation-cross-account
RotationRules: {ScheduleExpression: 'rate(1d)'}
LastRotatedDate: 2026-07-30T03:17:22Z

Rotation role (in account 222222222222) identity policy:
  Effect: Allow
  Action: [secretsmanager:GetSecretValue,
            secretsmanager:PutSecretValue,
            secretsmanager:DescribeSecret]
  Resource: arn:aws:secretsmanager:us-east-1:111111111111:secret:prod/payments/cross-account-secret-access-denied-Ab12Cd

Secret resource-based policy (account 111111111111):
  {
    "Version": "2012-10-17",
    "Statement": [
      {
        "Effect": "Allow",
        "Principal": {"AWS": "arn:aws:iam::111111111111:role/SecretsManagerRotation-role"},
        "Action": ["secretsmanager:GetSecretValue",
                    "secretsmanager:PutSecretValue"],
        "Resource": "*"
      }
    ]
  }
  Note: Principal lists the SAME account (111111111111); does
  not list the rotation role in account 222222222222.

KMS: secret uses alias/aws/secretsmanager (AWS-managed; no
cross-account KMS issue).

Recent rotation Lambda log pattern:
  [INFO]  createSecret: reading secret value
  [ERROR] AccessDeniedException: User
          arn:aws:sts::222222222222:assumed-role/SecretsManagerRotation-role/...
          is not authorized to perform: secretsmanager:GetSecretValue

CloudTrail (account 111111111111) lookup-events:
  EventName: GetSecretValue
  errorMessage: "User ... is not authorized to perform:
    secretsmanager:GetSecretValue on resource:
    arn:aws:secretsmanager:us-east-1:111111111111:secret:prod/payments/cross-account-secret-access-denied-Ab12Cd"
  sourceIPAddress: Lambda ENI in account 222222222222 VPC
  userIdentity.sessionContext.sessionIssuer.arn:
    arn:aws:iam::222222222222:role/SecretsManagerRotation-role
```

Cross-account secret access requires BOTH the rotation role's
identity-based policy (already correct in account 222222222222) AND
the secret's resource-based policy (in account 111111111111). The
resource policy here lists only the same-account role
(`arn:aws:iam::111111111111:role/...`) and does NOT grant the
cross-account rotation role in `222222222222`. This is a
`PERMISSION_CROSS_ACCOUNT` issue, not a same-account
`PERMISSION_ROTATION_ROLE` issue.
