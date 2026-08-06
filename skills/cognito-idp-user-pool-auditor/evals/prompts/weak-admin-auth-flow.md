# Eval prompt: weak-admin-auth-flow

**Difficulty:** medium
**Branch:** Rule 2a + 2f + 2h — MFA optional, ASF OFF, insecure OAuth redirects

## Prompt

Audit this Cognito user pool configuration for security posture.
Emit the standard VERDICT block (USER POOL, VERDICT, REASON, RISK, REMEDIATION).

```
User Pool: enterprise-b2b-pool
MfaConfiguration: OPTIONAL
EnabledMfas:
  - SOFTWARE_TOKEN_MFA
PasswordPolicy:
  MinimumLength: 12
  RequireUppercase: true
  RequireLowercase: true
  RequireNumbers: true
  RequireSymbols: true
  TemporaryPasswordValidityDays: 7
UserPoolAddOns:
  AdvancedSecurityMode: OFF
DeletionProtection: ACTIVE

App Client: web-portal-client
GenerateSecret: true
ExplicitAuthFlows:
  - ALLOW_USER_SRP_AUTH
  - ALLOW_REFRESH_TOKEN_AUTH
PreventUserExistenceErrors: ENABLED
EnableTokenRevocation: true
RefreshTokenValidity: 30
TokenValidityUnits:
  RefreshToken: days
AllowedOAuthFlows:
  - code
AllowedOAuthScopes:
  - openid
  - email
  - profile
CallbackURLs:
  - http://app.enterprise.example.com/callback
  - https://*.enterprise.example.com/callback
LogoutURLs:
  - http://app.enterprise.example.com/logout
```
