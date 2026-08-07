# Eval prompt: cross-account-rotation-access-denied-blocked

Diagnose the following cross-account Secrets Manager rotation failure and
emit the standard VERDICT block (OPERATION, VERDICT, TARGET, PRE_CHECKS,
STEPS, POST_VERIFY, NOTES).

Operation: diagnose-rotation
Secret: arn:aws:secretsmanager:us-east-1:111111111111:secret:prod/shared-api-key-ABC123
  (Secret lives in account 111111111111 / account A)
Rotation Lambda: arn:aws:lambda:us-east-1:222222222222:function:SharedApikeyRotationLambda
  (Lambda lives in account 222222222222 / account B)

```json
{
  "SecretMetadata": {
    "Name": "prod/shared-api-key",
    "RotationEnabled": true,
    "RotationLambdaARN": "arn:aws:lambda:us-east-1:222222222222:function:SharedApikeyRotationLambda",
    "RotationRules": {"AutomaticallyAfterDays": 14},
    "LastRotatedDate": null,
    "RotationEnabledForDays": 60,
    "KmsKeyId": "arn:aws:kms:us-east-1:111111111111:key/shared-api-cmk",
    "VersionIdsToStages": {"v1": ["AWSCURRENT"]}
  },
  "SecretResourcePolicy": {
    "Statement": [{
      "Effect": "Allow",
      "Principal": {"AWS": "arn:aws:iam::222222222222:role/SharedApikeyRotationRole"},
      "Action": [
        "secretsmanager:GetSecretValue",
        "secretsmanager:PutSecretValue",
        "secretsmanager:UpdateSecretVersionStage",
        "secretsmanager:DescribeSecret"
      ]
    }],
    "Status": "correctly configured on secret side"
  },
  "LambdaResourcePolicy": {
    "Statement": [{
      "Effect": "Allow",
      "Principal": {"Service": "sqs.amazonaws.com"},
      "Action": "lambda:InvokeFunction"
    }],
    "Missing": "Principal: {Service: secretsmanager.amazonaws.com}, Action: lambda:InvokeFunction"
  },
  "LambdaExecutionRole": {
    "HasPermissions": "secretsmanager:GetSecretValue etc on cross-account secret ARN, kms:Decrypt on cross-account KMS key ARN"
  },
  "KmsKeyPolicy": {
    "Grants": "arn:aws:iam::222222222222:role/SharedApikeyRotationRole kms:Decrypt"
  },
  "CloudWatchLogs": {
    "SampleError": "AccessDeniedException: User: arn:aws:sts::222222222222:assumed-role/SharedApikeyRotationRole/SecretsManager is not authorized to perform: lambda:InvokeFunction on resource: arn:aws:lambda:us-east-1:222222222222:function:SharedApikeyRotationLambda"
  }
}
```
