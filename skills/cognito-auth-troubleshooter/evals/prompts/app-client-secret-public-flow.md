# Eval prompt: app-client-secret-public-flow

Diagnose the Cognito authentication failure for the following User Pool
and app client. Walk the symptom-driven diagnostic tree and emit the
standard diagnostic block (TARGET, VERDICT, REASON, LAYER, EVIDENCE,
REMEDIATION).

Symptom: the React SPA calls Cognito `InitiateAuth` with
`USER_PASSWORD_AUTH` and includes a `client_secret` parameter. Every
token exchange returns `NotAuthorizedException` with
`error: invalid_client`.

```text
UserPoolId: us-east-1_XyZwVu987
AppClientId: 9pq8rs7tu6vw5xy4za3b2c1def
ClientName: mobile-spa-client

App Client configuration:
  ClientSecret: (null — created with GenerateClientSecret: false)
  ExplicitAuthFlows: ["ALLOW_USER_PASSWORD_AUTH",
    "ALLOW_REFRESH_TOKEN_AUTH"]
  PreventUserExistenceErrors: true

Frontend SDK call (amplify-js):
  Auth.signIn(username, password)
  // Internal: sends client_secret from env var
  // COGNITO_CLIENT_SECRET (leftover from a previous
  // CONFIDENTIAL client config)

Error response:
  { "error": "invalid_client",
    "error_description": "Invalid client credentials passed" }
```

The app client was created as a PUBLIC client (no secret). The frontend
is sending a leftover `client_secret` from a previous CONFIDENTIAL
client configuration. A PUBLIC client must NOT send a secret.
