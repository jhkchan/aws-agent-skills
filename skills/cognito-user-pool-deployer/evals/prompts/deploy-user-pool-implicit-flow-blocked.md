# Eval prompt: deploy-user-pool-implicit-flow-blocked

Plan the following Cognito user pool creation and emit the standard
VERDICT block. The app client requests OAuth implicit flow alongside
code flow.

Operation: create
Pool name: prod-users
Region: us-east-1
Account: 111111111111
Username attributes: ["email"]
Schema:
  - Name: email, Type: String, Required: true
PasswordPolicy: MinLength=12, all classes=true
MfaConfiguration: ON
EnabledMfas: ["TOTP"]
AdvancedSecurityMode: ENFORCED
DeletionProtection: ACTIVE
PreventUserExistenceErrors: ENABLED
App client:
  Name: legacy-spa
  GenerateClientSecret: false
  ExplicitAuthFlows: ALLOW_USER_SRP_AUTH, ALLOW_REFRESH_TOKEN_AUTH
  AllowedOAuthFlows: code, implicit
  AllowedOAuthScopes: openid email
  CallbackURLs: ["https://app.example.com/callback"]

```json
{
  "PreFlight": {
    "list-user-pools": "no pool named prod-users",
    "iam.get-role.CognitoOperatorRole": "OK"
  }
}
```
