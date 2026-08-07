# Eval prompt: kms-decrypt-cmk-role-missing

Diagnose the Lambda invocation failure for the following function. Walk
the symptom-driven diagnostic tree and emit the standard diagnostic
block (TARGET, VERDICT, REASON, LAYER, EVIDENCE, REMEDIATION).

Symptom: `fn-kms-decrypt-cmk-role-missing` fails to start after the
last deploy. Logs show `Could not decrypt KMS` on every invocation.
The deploy migrated environment variables from the default
`aws/lambda` key to a customer-managed CMK
(`arn:aws:kms:us-east-1:111111111111:key/abc-123`) per a security
team mandate.

```text
FunctionName: fn-kms-decrypt-cmk-role-missing
Qualifier: prod (version 23)
Runtime: nodejs20.x
Timeout: 30
MemorySize: 512
Handler: index.handler
KMSKeyArn: arn:aws:kms:us-east-1:111111111111:key/abc-123
Environment:
  Variables:
    DB_PASSWORD: <encrypted-blob>
    API_TOKEN: <encrypted-blob>
Execution role: arn:aws:iam::111111111111:role/fn-role
Execution role policies (attached):
  - AWSLambdaBasicExecutionRole
  - AmazonS3ReadOnlyAccess
  - inline: { db-access: { Effect: Allow, Action: [dynamodb:*],
      Resource: "*" } }
Execution role kms:Decrypt permission: NOT PRESENT

KMS key state: Enabled, KeyManager: CUSTOMER, Origin: AWS_KMS

Recent log pattern:
  Could not decrypt KMS: arn:aws:kms:us-east-1:111111111111:key/abc-123
  Runtime.ExitError
```

Customer-managed CMKs require `kms:Decrypt` on the execution role.
The default AWS-managed `aws/lambda` key does NOT require this
permission — Lambda decrypts transparently.
