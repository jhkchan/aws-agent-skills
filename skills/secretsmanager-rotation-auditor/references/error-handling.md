# Error Handling — Secrets Manager Rotation Auditor

> Moved verbatim from SKILL.md for progressive disclosure (agentskills.io). Load on demand.

## Malformed input — ERROR emit block

```text
SECRET: <name or "(unknown)">
VERDICT: ERROR
REASON: Secret config is incomplete or unparseable — cannot evaluate rotation posture.
REMEDIATION: Re-run aws secretsmanager describe-secret --secret-id <name> and provide the full output.
```

## Step 4a — invocation error code table

| Error code / pattern | Root cause | Classification note |
|---|---|---|
| `AccessDeniedException` on `secretsmanager:GetSecretValue` | Lambda execution role lacks Secrets Manager permissions | The role is missing `secretsmanager:GetSecretValue` or the resource-based policy on the secret denies the Lambda role. |
| `AccessDeniedException` on `kms:Decrypt` | KMS key policy denies the Lambda role | The KMS key encrypting the secret does not grant `kms:Decrypt` to the Lambda execution role. The Lambda can read the secret ARN but cannot decrypt the value. |
| `ResourceNotFoundException` on target (RDS, Redshift) | Target resource deleted or unreachable | The database instance was deleted but the secret remains. The Lambda's `setSecret` step cannot connect because the endpoint no longer exists. |
| `TimeoutException` / `Task timed out` | Lambda timeout too short | Database rotation involves connect + authenticate + ALTER USER — large databases with slow connections may exceed the default 30s timeout. |
| `OperationError` / `ConnectionRefused` | VPC misconfiguration | Lambda subnets or security groups cannot reach the target resource (wrong subnet, missing route, security group rule missing). |
| `InvalidParameterException` on `createSecret` | Secret value template malformed | The Lambda's secret-value generation template produces invalid characters for the target (e.g., `$` in a MySQL password). |

