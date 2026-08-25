# Diagnostic commands - Cognito User Pool Auditor (load on demand)

## Pre-flight safety checks - run before any remediation CLI (moved from SKILL.md)

- Confirm the pool exists and capture its current state for rollback:
  ```bash
  aws cognito-idp describe-user-pool \
    --user-pool-id <pool-id> \
    --output json > /tmp/<pool-id>-backup-$(date +%s).json
  aws cognito-idp list-user-pool-clients \
    --user-pool-id <pool-id> \
    --output json > /tmp/<pool-id>-clients-backup-$(date +%s).json
  aws cognito-idp describe-user-pool-client \
    --user-pool-id <pool-id> --client-id <client-id> \
    --output json > /tmp/<client-id>-backup-$(date +%s).json
  ```

- Prefer additive changes over destructive changes:
  - Enabling `PreventUserExistenceErrors: ENABLED` is additive (more secure,
    no client-side impact).
  - Enabling `EnableTokenRevocation: true` is additive (adds `jti` claim to
    new tokens; existing tokens are unaffected until they expire).
  - Removing an auth flow from `ExplicitAuthFlows` is potentially
    destructive (breaks clients that depend on it). Test first.
  - Changing `MfaConfiguration` from `OFF`/`OPTIONAL` to `ON` is potentially
    destructive (locks out users without an enrolled MFA factor).

- For INSECURE pools (OAuth implicit flow, admin auth on public client),
  treat as incident response:
  1. Disable the vulnerable app client immediately (set the auth flow or
     OAuth flow to the secure alternative, or if unsure, delete and
     recreate the client with correct settings).
  2. Audit CloudTrail for `AdminInitiateAuth` and `InitiateAuth` events on
     the affected client during the exposure window.
  3. Force password reset for users who authenticated via the vulnerable
     flow during the exposure window (breached credentials may have been
     captured).

- For token-related changes (`RefreshTokenValidity`,
  `AccessTokenValidity`, `IdTokenValidity`): existing tokens remain valid
  until they expire. The new validity applies only to tokens issued after
  the change. No immediate user impact, but monitor for session-extension
  failures if validity was shortened.

