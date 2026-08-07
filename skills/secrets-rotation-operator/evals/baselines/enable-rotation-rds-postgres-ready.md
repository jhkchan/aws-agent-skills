# Baseline (no-skill) response: enable-rotation-rds-postgres-ready

This file captures what a generic assistant produces WITHOUT the
secrets-rotation-operator skill loaded.

---

To enable rotation on your secret, use the following command:

```bash
aws secretsmanager rotate-secret \
  --secret-id prod/payments-db-credentials \
  --rotation-lambda-arn arn:aws:lambda:us-east-1:111111111111:function:SecretsManagerRDSPostgreSQLRotation \
  --rotation-rules AutomaticallyAfterDays=30
```

This will trigger the first rotation immediately. Make sure your Lambda
function has the necessary IAM permissions to access the secret and the
RDS instance. After the rotation completes, you can verify with
`aws secretsmanager describe-secret`.
