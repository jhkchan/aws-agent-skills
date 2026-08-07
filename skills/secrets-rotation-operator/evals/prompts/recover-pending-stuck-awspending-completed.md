# Eval prompt: recover-pending-stuck-awspending-completed

Plan and verify the following Secrets Manager AWSPENDING recovery
operation and emit the standard VERDICT block (OPERATION, VERDICT,
TARGET, PRE_CHECKS, STEPS, POST_VERIFY, NOTES). The fix has already been
executed; produce the post-verification COMPLETED form.

Operation: recover-pending
Secret: prod/api-gateway-token

```json
{
  "SecretMetadata": {
    "Name": "prod/api-gateway-token",
    "RotationEnabled": true,
    "RotationLambdaARN": "arn:aws:lambda:us-east-1:111111111111:function:ApiGatewayTokenRotation",
    "LastRotatedDate": "2026-07-15T03:00:00Z",
    "VersionIdsToStages": {
      "e5f6g7h8": ["AWSPREVIOUS"],
      "i9j0k1l2": ["AWSCURRENT"],
      "a1b2c3d4": ["AWSPENDING"]
    },
    "PrimaryRegion": null,
    "DeletedDate": null
  },
  "ConnectionTests": {
    "AWSPENDING": "SUCCESS (new credential is live on the target)",
    "AWSCURRENT": "FAILED (old credential already replaced)"
  },
  "RootCause": "finishSecret step failed with AccessDeniedException on UpdateSecretVersionStage. Execution role has been updated.",
  "ExecutionResult": {
    "Command": "aws secretsmanager update-secret-version-stage --secret-id prod/api-gateway-token --version-stage AWSCURRENT --move-to-version-id a1b2c3d4 --remove-from-version-id i9j0k1l2",
    "Result": "success",
    "PostExecutionVersionStages": {
      "a1b2c3d4": ["AWSCURRENT"],
      "i9j0k1l2": ["AWSPREVIOUS"],
      "e5f6g7h8": [],
      "AWSPENDING": "none"
    },
    "ApplicationMetrics": "no auth failures in 5-min sample post-fix"
  }
}
```
