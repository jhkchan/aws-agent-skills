# Baseline (no-skill) response: fargate-essential-container-secret-injection

This file captures what a generic assistant produces WITHOUT the
ecs-task-troubleshooter skill loaded — the contrast that proves the
skill adds structure (deterministic VERDICT, category-aware walk,
specific remediation).

---

Your ECS task is exiting immediately. The error message says it cannot
retrieve a secret from Secrets Manager. This means the task execution
role does not have permission to read the secret.

You should add `secretsmanager:GetSecretValue` permission to the
execution role. You can attach the `SecretsManagerReadWrite` managed
policy or create an inline policy that allows the action on the
specific secret ARN.

Also check that the secret ARN in the task definition `secrets` array
matches the actual secret in Secrets Manager. Sometimes the 6-character
suffix on the ARN changes after rotation, so you may need to use a
wildcard.
