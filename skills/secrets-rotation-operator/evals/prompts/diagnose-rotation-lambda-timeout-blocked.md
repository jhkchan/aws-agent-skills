# Eval prompt: diagnose-rotation-lambda-timeout-blocked

Diagnose the following Secrets Manager rotation failure and emit the
standard VERDICT block (OPERATION, VERDICT, TARGET, PRE_CHECKS, STEPS,
POST_VERIFY, NOTES).

Operation: diagnose-rotation
Secret: prod/payments-db-credentials

```json
{
  "SecretMetadata": {
    "Name": "prod/payments-db-credentials",
    "RotationEnabled": true,
    "RotationLambdaARN": "arn:aws:lambda:us-east-1:111111111111:function:SecretsManagerRDSPostgreSQLRotation",
    "RotationRules": {"AutomaticallyAfterDays": 30},
    "LastRotatedDate": "2026-07-15T03:00:00Z",
    "LastChangedDate": "2026-06-15T03:00:00Z",
    "VersionIdsToStages": {
      "v1": ["AWSPREVIOUS"],
      "v2": ["AWSCURRENT"]
    },
    "AWSPENDING": "none"
  },
  "LambdaMetadata": {
    "FunctionName": "SecretsManagerRDSPostgreSQLRotation",
    "State": "Active",
    "Runtime": "python3.12",
    "Timeout": 3,
    "ReservedConcurrentExecutions": 5
  },
  "CloudWatchLogs": {
    "ErrorPattern": "Task timed out after 3.00 seconds",
    "Occurrences": "every day at 03:00 UTC for the last 14 days",
    "SampleEntries": [
      "2026-08-05 03:00:14 TASK FAILED: Task timed out after 3.00 seconds",
      "2026-08-04 03:00:11 TASK FAILED: Task timed out after 3.00 seconds",
      "2026-08-03 03:00:09 TASK FAILED: Task timed out after 3.00 seconds"
    ]
  },
  "IamRolePermissions": "verified complete (SecretsManagerRotation, AWSLambdaVPCAccessExecutionRole, rds-db:connect, kms:Decrypt)",
  "KmsKey": "verified Enabled, policy grants Lambda role",
  "VpcReachability": "verified OK (DB SG allows Lambda SG on 5432)"
}
```
