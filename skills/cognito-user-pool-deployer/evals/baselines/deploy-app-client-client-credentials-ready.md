# Baseline (no-skill) response: deploy-app-client-client-credentials-ready

This file captures what a generic assistant produces WITHOUT the
cognito-user-pool-deployer skill loaded.

---

To create a machine-to-machine client:

```bash
aws cognito-idp create-user-pool-client \
  --user-pool-id us-east-1_abc123 \
  --client-name m2m-orders-service \
  --generate-client-secret \
  --allowed-o-auth-flows client-credentials \
  --allowed-o-auth-scopes "products.read"
```

You may need to set up a resource server first.
