# Baseline (no-skill) response: trigger-rotation-reserved-concurrency-zero-blocked

This file captures what a generic assistant produces WITHOUT the
secrets-rotation-operator skill loaded.

---

To trigger a manual rotation on the secret:

```bash
aws secretsmanager rotate-secret --secret-id prod/orders-service-token
```

You may also want to verify that the rotation Lambda is configured
correctly. If rotation is failing, check CloudWatch Logs for the Lambda
function `OrdersServiceTokenRotation`.
