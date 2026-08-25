# Diagnostic Commands — Secrets Manager Rotation Operator

> Moved verbatim from SKILL.md for progressive disclosure (agentskills.io). Load on demand.

## Live-account pre-flight (secret metadata gate)

1. `aws secretsmanager describe-secret --secret-id <id>` — confirm secret
   exists; capture `RotationEnabled`, `RotationLambdaARN`,
   `RotationRules`, `LastRotatedDate`, `LastChangedDate`, `KmsKeyId`,
   `VersionIdsToStages`, `DeletedDate`, `PrimaryRegion`, `OwningService`.
2. `aws secretsmanager get-resource-policy --secret-id <id>` — capture
   the cross-account resource-based policy (if any).
3. `aws lambda get-function-configuration --function-name <lambda>` —
   confirm `State: Active`; capture `Runtime`, `Timeout`, `MemorySize`,
   `VpcConfig`, `Role`, `ReservedConcurrentExecutions`.
4. `aws lambda get-policy --function-name <lambda>` — confirm the
   resource-based policy allows `lambda:InvokeFunction` from
   `secretsmanager.amazonaws.com` (and the secret's account, if cross-
   account).
5. `aws lambda get-function-concurrency --function-name <lambda>` —
   confirm reserved concurrency is not 0.
6. `aws iam list-attached-role-policies --role-name <role>` and
   `aws iam list-role-policies --role-name <role>` — verify the execution-
   role permission chain.
7. `aws kms describe-key --key-id <kms-id>` — confirm key `Enabled` and
   the policy grants the Lambda role `kms:Decrypt` (customer-managed keys
   only; default `aws/secretsmanager` is account-scoped).
8. `aws logs filter-log-events --log-group-name /aws/lambda/<lambda>
   --filter-pattern ERROR --limit 20` — capture the last rotation errors.

