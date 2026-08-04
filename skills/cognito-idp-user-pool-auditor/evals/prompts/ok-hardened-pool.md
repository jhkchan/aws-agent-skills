# Eval prompt: ok-hardened-pool

**Expected verdict:** OK
**Difficulty:** easy
**Branch:** Rule 4 — all controls met

## Prompt

Audit this Cognito user pool configuration for security posture.
Emit the standard VERDICT block (USER POOL, VERDICT, REASON, RISK, REMEDIATION).

```
User Pool: hardened-prod-pool
MfaConfiguration: ON
EnabledMfas:
  - SOFTWARE_TOKEN_MFA
PasswordPolicy:
  MinimumLength: 14
  RequireUppercase: true
  RequireLowercase: true
  RequireNumbers: true
  RequireSymbols: true
  TemporaryPasswordValidityDays: 3
UserPoolAddOns:
  AdvancedSecurityMode: ENFORCED
DeletionProtection: ACTIVE
AccountRecoverySetting:
  RecoveryMechanisms:
    - Name: verified_email
      Priority: 1
    - Name: verified_phone_number
      Priority: 2

App Client: prod-web-client
GenerateSecret: true
ExplicitAuthFlows:
  - ALLOW_USER_SRP_AUTH
  - ALLOW_REFRESH_TOKEN_AUTH
PreventUserExistenceErrors: ENABLED
EnableTokenRevocation: true
RefreshTokenValidity: 7
TokenValidityUnits:
  RefreshToken: days
  AccessToken: hours
  IdToken: hours
AccessTokenValidity: 1
IdTokenValidity: 1
AllowedOAuthFlows:
  - code
AllowedOAuthScopes:
  - openid
  - email
  - profile
CallbackURLs:
  - https://app.example.com/callback
LogoutURLs:
  - https://app.example.com/logout
```
