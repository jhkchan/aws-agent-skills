# Eval prompt: hosted-ui-callback-mismatch

Diagnose the Cognito authentication failure for the following User Pool
and app client. Walk the symptom-driven diagnostic tree and emit the
standard diagnostic block (TARGET, VERDICT, REASON, LAYER, EVIDENCE,
REMEDIATION).

Symptom: all users see `redirect_mismatch` error after entering
credentials on the Cognito hosted UI. The browser address bar shows
`redirect_uri=https://app.example.com/auth/callback`.

```text
UserPoolId: us-east-1_AbCdEf123
AppClientId: 1ab2cd3ef4gh5ij6lmn7opq8rs
ClientName: web-app-client
AuthFlow: code grant (hosted UI /oauth2/authorize)
Domain: auth.example.com (Cognito custom domain)

App Client configuration:
  CallbackURLs: ["https://app.example.com/callback"]
  LogoutURLs: ["https://app.example.com/logout"]
  AllowedOAuthFlows: ["code"]
  AllowedOAuthScopes: ["openid", "email", "profile"]
  SupportedIdentityProviders: ["COGNITO"]
  ClientSecret: (null — PUBLIC client)
  ExplicitAuthFlows: ["ALLOW_USER_SRP_AUTH",
    "ALLOW_REFRESH_TOKEN_AUTH"]

Application config (from frontend):
  redirect_uri: https://app.example.com/auth/callback
```

The hosted UI validates redirect_uri against CallbackURLs at the
authorization endpoint. Check scheme, host, port, and path for exact
match.
