# Eval prompt: deploy-standard-user-pool-ready

Plan the following Cognito user pool creation and emit the standard
VERDICT block (POOL, VERDICT, TARGET, PRE_CHECKS, STEPS, POST_VERIFY,
ATTRIBUTES, MFA, OAUTH_FLOWS, IDPS, ASF, NOTES).

Operation: create
Pool name: prod-users
Region: us-east-1
Account: 111111111111
Username attributes: ["email"]
Schema:
  - Name: email, Type: String, Required: true, Mutable: false
  - Name: given_name, Type: String, Required: true
  - Name: family_name, Type: String, Required: true
  - Name: custom:tenantId, Type: String, Required: false, Mutable: false
PasswordPolicy: MinLength=16, all classes=true, TempValidity=1 day
MfaConfiguration: ON
EnabledMfas: ["TOTP"]
AdvancedSecurityMode: ENFORCED
DeletionProtection: ACTIVE
PreventUserExistenceErrors: ENABLED
App client:
  Name: prod-web-spa
  GenerateClientSecret: true
  ExplicitAuthFlows: ALLOW_USER_SRP_AUTH, ALLOW_REFRESH_TOKEN_AUTH
  AllowedOAuthFlows: code
  AllowedOAuthScopes: openid email profile
  CallbackURLs: ["https://app.example.com/callback"]
  LogoutURLs: ["https://app.example.com/logout"]
  AccessTokenValidity: 1 hour
  IdTokenValidity: 1 hour
  RefreshTokenValidity: 30 days
  EnableTokenRevocation: true

```json
{
  "PreFlight": {
    "list-user-pools": "no pool named prod-users",
    "iam.get-role.CognitoOperatorRole": "OK"
  }
}
```
