# Baseline (no-skill) response: deploy-standard-user-pool-ready

This file captures what a generic assistant produces WITHOUT the
cognito-user-pool-deployer skill loaded.

---

To create your Cognito user pool, run:

```bash
aws cognito-idp create-user-pool \
  --pool-name prod-users \
  --policies '{"PasswordPolicy":{"MinimumLength":16,"RequireUppercase":true,"RequireLowercase":true,"RequireNumbers":true,"RequireSymbols":true}}' \
  --mfa-configuration ON \
  --username-attributes '["email"]'

aws cognito-idp create-user-pool-client \
  --user-pool-id <id> \
  --client-name prod-web-spa \
  --explicit-auth-flows ALLOW_USER_SRP_AUTH ALLOW_REFRESH_TOKEN_AUTH \
  --allowed-o-auth-flows code \
  --callback-urls '["https://app.example.com/callback"]'
```

You can add custom attributes later if needed.
