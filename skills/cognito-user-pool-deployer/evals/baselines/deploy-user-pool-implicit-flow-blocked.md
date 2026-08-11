# Baseline (no-skill) response: deploy-user-pool-implicit-flow-blocked

This file captures what a generic assistant produces WITHOUT the
cognito-user-pool-deployer skill loaded.

---

To create your user pool:

```bash
aws cognito-idp create-user-pool \
  --pool-name prod-users \
  --mfa-configuration ON \
  --username-attributes '["email"]'

aws cognito-idp create-user-pool-client \
  --user-pool-id <id> \
  --client-name legacy-spa \
  --explicit-auth-flows ALLOW_USER_SRP_AUTH ALLOW_REFRESH_TOKEN_AUTH \
  --allowed-o-auth-flows code implicit \
  --allowed-o-auth-scopes openid email \
  --callback-urls '["https://app.example.com/callback"]'
```

Note: implicit flow is convenient for SPAs that cannot securely store
a client secret.
