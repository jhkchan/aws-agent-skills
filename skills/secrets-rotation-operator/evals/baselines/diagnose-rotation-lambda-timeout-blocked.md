# Baseline (no-skill) response: diagnose-rotation-lambda-timeout-blocked

This file captures what a generic assistant produces WITHOUT the
secrets-rotation-operator skill loaded.

---

Looking at your CloudWatch Logs, the rotation Lambda is timing out after
3 seconds. The default Lambda timeout is 3 seconds which may be too
short for database rotations. You should increase the timeout:

```bash
aws lambda update-function-configuration \
  --function-name SecretsManagerRDSPostgreSQLRotation \
  --timeout 30
```

Then trigger a manual rotation to test:

```bash
aws secretsmanager rotate-secret --secret-id prod/payments-db-credentials
```
