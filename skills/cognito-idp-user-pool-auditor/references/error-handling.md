# Error handling - Cognito User Pool Auditor (load on demand)

## Remediation guidance (moved from SKILL.md)

### For INSECURE pools

**Rule 1a (no MFA + weak password):**
1. Strengthen the password policy immediately:
   ```bash
   aws cognito-idp update-user-pool \
     --user-pool-id <pool-id> \
     --policies '{
       "PasswordPolicy": {
         "MinimumLength": 12,
         "RequireUppercase": true,
         "RequireLowercase": true,
         "RequireNumbers": true,
         "RequireSymbols": true,
         "TemporaryPasswordValidityDays": 7
       }
     }'
   ```
2. Enable MFA in a phased rollout: set `MfaConfiguration: OPTIONAL` first,
   communicate to users, monitor enrollment, then transition to `ON` when
   enrollment exceeds 90%.
3. Enable `AdvancedSecurityMode: ENFORCED` to add compromised-credential
   detection.

**Rule 1b (OAuth implicit flow):**
1. Switch `AllowedOAuthFlows` to `["code"]` only:
   ```bash
   aws cognito-idp update-user-pool-client \
     --user-pool-id <pool-id> \
     --client-id <client-id> \
     --allowed-o-auth-flows code
   ```
2. Ensure the client SDK uses PKCE (Amazon Cognito Amplify v6+ uses PKCE
   by default for the authorization code flow).
3. If the application architecture requires implicit (e.g., a legacy SPA
   that cannot perform a back-channel token exchange), migrate to a
   backend-for-frontend (BFF) pattern or a server-side OAuth library.

**Rule 1c (PreventUserExistenceErrors LEGACY):**
1. Update the app client:
   ```bash
   aws cognito-idp update-user-pool-client \
     --user-pool-id <pool-id> \
     --client-id <client-id> \
     --prevent-user-existence-errors ENABLED
   ```
2. This is an additive change — no client-side impact. Error messages
   change from specific (`UserNotFoundException`) to generic
   (`NotAuthorizedException`) for all auth failures.

**Rule 1d/1e:** See Rule 1a for MFA/ASF remediation. For admin auth on
public client (Rule 1d), remove `ALLOW_ADMIN_USER_PASSWORD_AUTH` from
`ExplicitAuthFlows` and replace with `ALLOW_USER_SRP_AUTH` +
`ALLOW_REFRESH_TOKEN_AUTH`.

### For WEAK pools

- **Rule 2a (MFA optional):** Transition to `MfaConfiguration: ON` after
  a communication and enrollment campaign. Provide a self-service MFA
  setup flow to maximize enrollment before enforcement.
- **Rule 2d (non-SRP auth):** Remove `ALLOW_USER_PASSWORD_AUTH` if the
  client SDK supports SRP. For Amazon Cognito Amplify v6+, SRP is the
  default. Test in staging first.
- **Rule 2e (long refresh token):** Reduce `RefreshTokenValidity` to 7-30
  days depending on sensitivity. For financial/healthcare apps, use 1-7
  days.
- **Rule 2f (ASF not enforced):** Transition `AdvancedSecurityMode` from
  `AUDIT` to `ENFORCED` after reviewing the audit logs for false positives
  (typically 1-2 weeks of monitoring).

### For ADEQUATE pools

- **Rule 3a (ASF audit mode):** Set a timeline for transitioning to
  `ENFORCED`. Review ASF audit findings for false-positive patterns.
- **Rule 3e (SMS-only MFA):** Enable TOTP:
  ```bash
  aws cognito-idp update-user-pool \
    --user-pool-id <pool-id> \
    --mfa-configuration ON \
    --sms-configuration ... \
    --software-token-mfa-configuration Enabled=true
  ```
  Users can then choose TOTP (recommended) or SMS.

### For OK pools

- No remediation required.
- Periodically review ASF findings and CloudTrail for suspicious auth
  patterns.
- Review app-client inventory for unused clients (delete clients that are
  no longer in use to reduce attack surface).

