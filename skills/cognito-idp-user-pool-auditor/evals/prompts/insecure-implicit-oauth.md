# Eval prompt: insecure-implicit-oauth

**Difficulty:** medium
**Branch:** Rule 1b — implicit OAuth overrides otherwise strong controls

## Prompt

Audit this Cognito user pool configuration for security posture.
Emit the standard VERDICT block (USER POOL, VERDICT, REASON, RISK, REMEDIATION).

```
User Pool: spa-app-pool
MfaConfiguration: ON
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
  AdvancedSecurityMode: ENFORCED
DeletionProtection: ACTIVE

App Client: spa-client
GenerateSecret: false
ExplicitAuthFlows:
  - ALLOW_USER_SRP_AUTH
  - ALLOW_REFRESH_TOKEN_AUTH
PreventUserExistenceErrors: ENABLED
EnableTokenRevocation: true
RefreshTokenValidity: 30
TokenValidityUnits:
  RefreshToken: days
AllowedOAuthFlows:
  - implicit
AllowedOAuthScopes:
  - openid
  - email
  - profile
CallbackURLs:
  - https://app.example.com/callback
```
