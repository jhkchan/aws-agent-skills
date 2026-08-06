# Eval prompt: adequate-enforced-mfa-minor-gaps

**Difficulty:** hard
**Branch:** Rule 3a + 3e — ASF not enforced, SMS-only MFA

## Prompt

Audit this Cognito user pool configuration for security posture.
Emit the standard VERDICT block (USER POOL, VERDICT, REASON, RISK, REMEDIATION).

```
User Pool: saas-platform-pool
MfaConfiguration: ON
EnabledMfas:
  - SMS
PasswordPolicy:
  MinimumLength: 10
  RequireUppercase: true
  RequireLowercase: true
  RequireNumbers: true
  RequireSymbols: true
  TemporaryPasswordValidityDays: 7
UserPoolAddOns:
  AdvancedSecurityMode: AUDIT
DeletionProtection: ACTIVE

App Client: web-app-client
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
CallbackURLs:
  - https://app.saas-platform.com/callback
```
