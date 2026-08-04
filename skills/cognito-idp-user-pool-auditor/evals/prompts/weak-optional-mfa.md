# Eval prompt: weak-optional-mfa

**Expected verdict:** WEAK
**Difficulty:** medium
**Branch:** Rule 2a + 2e — MFA optional, long-lived tokens

## Prompt

Audit this Cognito user pool configuration for security posture.
Emit the standard VERDICT block (USER POOL, VERDICT, REASON, RISK, REMEDIATION).

```
User Pool: consumer-app-pool
MfaConfiguration: OPTIONAL
EnabledMfas:
  - SOFTWARE_TOKEN_MFA
  - SMS
PasswordPolicy:
  MinimumLength: 8
  RequireUppercase: true
  RequireLowercase: true
  RequireNumbers: true
  RequireSymbols: false
  TemporaryPasswordValidityDays: 7
UserPoolAddOns:
  AdvancedSecurityMode: AUDIT
DeletionProtection: INACTIVE

App Client: mobile-client
GenerateSecret: true
ExplicitAuthFlows:
  - ALLOW_USER_SRP_AUTH
  - ALLOW_REFRESH_TOKEN_AUTH
PreventUserExistenceErrors: ENABLED
EnableTokenRevocation: true
RefreshTokenValidity: 90
TokenValidityUnits:
  RefreshToken: days
AllowedOAuthFlows:
  - code
CallbackURLs:
  - https://mobile.example.com/callback
```
