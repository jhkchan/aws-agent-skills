# Error Handling — Secrets Manager Rotation Operator

> Moved verbatim from SKILL.md for progressive disclosure (agentskills.io). Load on demand.

## Rotation failure-mode table (use during diagnose-rotation)

| Symptom in CloudWatch Logs | Root cause | Fix |
|---|---|---|
| `AccessDeniedException` on `secretsmanager:GetSecretValue` | Lambda role lacks Secrets Manager permissions or resource-based policy on the secret denies the role | Attach `SecretsManagerRotation` or scoped custom policy; add the role to the secret resource policy |
| `AccessDeniedException` on `kms:Decrypt` / `DecryptionFailureException` | KMS key policy denies the Lambda role | Add `kms:Decrypt` grant for the Lambda role to the key policy |
| `ResourceNotFoundException` on the target (RDS/Redshift/DocDB) | Target instance deleted or wrong endpoint in the secret | Update the secret's `host`/`port` fields, or delete the orphaned secret |
| `Task timed out after X seconds` | Lambda timeout too short | `update-function-configuration --timeout 30` (or 60 for Aurora) |
| `OperationError` / `ConnectionRefused` / `ETIMEDOUT` | VPC misconfiguration | Add the Lambda SG to the DB SG ingress; verify subnet route table |
| `InvalidParameterException` on `createSecret` | Secret value template produces invalid chars (e.g., `/` in MySQL password) | Adjust the password generator in the Lambda; use `string.printable - special_chars` |
| `AccessDeniedException` on `rds-db:connect` | Lambda role missing `rds-db:connect` on the DB ARN | Attach a policy granting `rds-db:connect` on `arn:aws:rds-db:<region>:<account>:dbuser:<db-resource-id>/<db-user>` |
| `Throttles` metric spike, no error logs | Reserved concurrency = 0 | `put-function-concurrency --reserved-concurrent-executions 1` |
| No invocations at all | Resource-based policy missing `secretsmanager.amazonaws.com` principal | Add the principal to the Lambda resource-based policy |
| `InvalidParameterException` enabling rotation on replica | Secret is a replica | Enable rotation on the primary in `PrimaryRegion` |

