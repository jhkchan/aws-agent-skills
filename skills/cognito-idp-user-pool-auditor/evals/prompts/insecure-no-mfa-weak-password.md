# Eval prompt: insecure-no-mfa-weak-password

**Expected verdict:** INSECURE
**Difficulty:** easy
**Branch:** Rule 1a + 1c + 1d — multiple critical deficiencies

## Prompt

Audit this Cognito user pool configuration for security posture.
Emit the standard VERDICT block (USER POOL, VERDICT, REASON, RISK, REMEDIATION).

```
User Pool: insecure-demo-pool
MfaConfiguration: OFF
EnabledMfas: []
PasswordPolicy:
  MinimumLength: 6
  RequireUppercase: false
  RequireLowercase: false
  RequireNumbers: false
  RequireSymbols: false
  TemporaryPasswordValidityDays: 7
UserPoolAddOns:
  AdvancedSecurityMode: OFF
DeletionProtection: INACTIVE

App Client: web-client
GenerateSecret: false
ExplicitAuthFlows:
  - ALLOW_USER_PASSWORD_AUTH
PreventUserExistenceErrors: LEGACY
EnableTokenRevocation: false
RefreshTokenValidity: 30
TokenValidityUnits:
  RefreshToken: days
AllowedOAuthFlows: []
```
