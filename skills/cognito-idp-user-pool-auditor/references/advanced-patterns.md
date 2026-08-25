# Advanced patterns - Cognito User Pool Auditor (load on demand)

## Auth-flow strength matrix (moved from SKILL.md)

> **Reference material** — consult this matrix when an app client's
> `ExplicitAuthFlows` contains flows beyond the standard SRP + refresh
> pair. The quick-reference summary and Steps 1-2 cover the common cases;
> this matrix provides the depth for edge-case flows.

When evaluating `ExplicitAuthFlows`, classify each flow to determine whether
the client uses the strongest available credential path:

**STRONG flows (do not affect verdict):**
- `ALLOW_USER_SRP_AUTH` — SRP (Secure Remote Password) protocol. The
  password is never transmitted. Uses a zero-knowledge proof: the client
  derives a verifier from the password and proves knowledge of the password
  without revealing it. Immune to replay attacks and TLS interception at
  the application layer.
- `ALLOW_REFRESH_TOKEN_AUTH` — exchanges a refresh token for new access/id
  tokens. No password involved. Safe as long as the refresh token is stored
  securely (HttpOnly cookie for web, Keychain/Keystore for mobile).

**MODERATE flows (Rule 3d if SRP is also present, Rule 2d if not):**
- `ALLOW_USER_PASSWORD_AUTH` — sends the username and password directly to
  the `InitiateAuth` API. The password travels over TLS (transport-level
  protection) but is exposed to the application layer (API logs, WAF
  inspection, TLS-terminating proxies). Required by some legacy SDKs and
  migration scenarios.

**WEAK flows (Rule 2g if confidential client, Rule 1d if public client):**
- `ALLOW_ADMIN_USER_PASSWORD_AUTH` (legacy name: `ADMIN_NO_SRP_AUTH`) —
  sends the username and password to `AdminInitiateAuth`, which requires
  AWS credentials (SigV4-signed request). Bypasses SRP entirely. The
  required AWS credentials expand the attack surface — if those credentials
  are in a Lambda function, ECS task, or EC2 instance that is compromised,
  the attacker can authenticate as any user. Acceptable only on a dedicated
  backend service client with `GenerateSecret: true`.

**VARIABLE flows (evaluate context):**
- `ALLOW_CUSTOM_AUTH` — uses Lambda triggers for custom authentication
  logic. Security depends entirely on the Lambda implementation. Flag for
  manual review of the trigger code.

## OAuth flow strength matrix (moved from SKILL.md)

When evaluating `AllowedOAuthFlows`, classify the OAuth grant type:

**STRONG:**
- `code` (authorization code flow) with PKCE — the authorization code is
  returned via the URL query string and exchanged for tokens via a
  back-channel request. PKCE (Proof Key for Code Exchange) prevents
  authorization-code interception by requiring the client to prove it
  possesses the code verifier. PKCE is mandatory for public clients (mobile,
  SPA) per OAuth 2.1.

**MODERATE:**
- `code` without PKCE — the authorization code is still exchanged
  server-side (safer than implicit), but without PKCE the code can be
  intercepted by a malicious app on the same device (mobile) or via a
  redirect-uri collision (web). Cognito does not have a separate PKCE
  setting — PKCE usage depends on the client SDK. Flag as ADEQUATE and
  recommend confirming PKCE is used by the client.

**WEAK (Rule 1b — INSECURE):**
- `implicit` — the access token (and optionally the ID token) is returned
  directly in the URL fragment. No back-channel exchange. The token is
  exposed via browser history, Referer headers, and any script on the
  callback page. OAuth 2.1 removes implicit flow entirely.

**NOT APPLICABLE (evaluate separately):**
- `client_credentials` — machine-to-machine authentication (no user
  involved). Not a user-authentication flow. If the app client is supposed
  to authenticate users and only has `client_credentials`, the
  configuration is broken (flag as ERROR). If the client is a dedicated
  service-to-service client, `client_credentials` is correct and does not
  affect the verdict.

## Multi-client and edge-case handling (moved from SKILL.md)

- **Hosted UI domain.** The Cognito Hosted UI (`<domain>.auth.<region>.
  amazoncognito.com` or a custom domain) is the pre-built login page for
  OAuth flows. If the Hosted UI is enabled, evaluate the `CallbackURLs` and
  `LogoutURLs` for HTTPS-only, no wildcards. A Hosted UI with HTTP callbacks
  leaks the authorization code over an unencrypted connection.

- **Legacy pool defaults.** Cognito pools created before February 2020
  default to `PreventUserExistenceErrors: LEGACY`. Pools created after
  default to `ENABLED`. Always verify the actual value — do not assume
  based on pool age.

- **EnabledMfas vs MfaConfiguration.** `MfaConfiguration` controls whether
  MFA is required (`ON`), optional (`OPTIONAL`), or disabled (`OFF`).
  `EnabledMfas` controls which MFA methods are available. A pool with
  `MfaConfiguration: ON` but `EnabledMfas: []` is a broken configuration —
  MFA is required but no methods are configured, so no user can authenticate.
  Flag as ERROR.

- **Token validity units.** `TokenValidityUnits` specifies the time unit
  (hours, days) for each token type. `RefreshTokenValidity: 30` with
  `TokenValidityUnits.RefreshToken: "days"` = 30 days. The same value with
  `"hours"` = 30 hours (under 2 days — likely a misconfiguration). Always
  check the unit alongside the value. A common Terraform misconfiguration is
  setting `refresh_token_validity = 1` expecting 1 day, but the default unit
  is `"days"` — if the provider sends `"hours"`, the refresh token expires in
  1 hour, causing constant re-authentication.

- **Token revocation mechanics.** `EnableTokenRevocation: true` adds two
  claims to issued JWTs: `jti` (a unique token ID) and `origin_jti` (the ID
  of the originating token in the session chain). When a token is revoked
  via `GlobalSignOut` or `RevokeToken`, Cognito adds the `jti` to a
  revocation list. Subsequent requests with that `jti` are rejected.
  Without `EnableTokenRevocation`, a stolen access token is valid until its
  `AccessTokenValidity` expires (typically 1 hour) and a stolen refresh
  token is valid until `RefreshTokenValidity` expires (can be days or
  weeks). The revocation list is eventually consistent — there is a brief
  window (seconds) between revocation and enforcement.

- **Cognito refresh token rotation limitation.** Unlike some OAuth providers
  (Auth0, Okta), Cognito does NOT support refresh token rotation — each
  use of a refresh token returns the SAME refresh token (not a new one),
  and the token remains valid until `RefreshTokenValidity` expires. This
  means a stolen refresh token cannot be detected via rotation anomaly.
  The only mitigations are: (1) short `RefreshTokenValidity`, and (2)
  `EnableTokenRevocation: true` so the token can be revoked if theft is
  detected. Flag pools with `RefreshTokenValidity` > 30 days AND
  `EnableTokenRevocation: false` as especially vulnerable to persistent
  token theft.

- **Legacy pool defaults.** Cognito pools created before February 2020
  default to `PreventUserExistenceErrors: LEGACY` (user enumeration risk).
  Pools created after default to `ENABLED`. Similarly, `EnableTokenRevocation`
  defaults to `false` on pools created before March 2021 and `true` after.
  Always verify the actual configured values — do not assume based on pool
  age. Run `aws cognito-idp describe-user-pool-client` to confirm.

- **Account recovery.** `AccountRecoverySetting.RecoveryMechanisms` with
  only `verified_email` means a compromised email account enables account
  takeover. `verified_email_and_phone` (email + SMS) provides defense in
  depth. Flag single-factor recovery as WEAK if the pool otherwise qualifies
  for ADEQUATE.

- **AdminCreateUserConfig.AllowAdminCreateUserOnly.** When `true`, only
  administrators can create user accounts (no self-signup). This is a
  security control for B2B or internal applications. When `false`, users
  can self-register — evaluate whether this is appropriate for the
  application's threat model.

- **Lambda triggers.** Security-relevant Lambda triggers:
  - `PreAuthentication` — can block logins based on custom conditions
    (e.g., IP allowlist).
  - `PostAuthentication` — runs after successful auth (e.g., audit logging).
  - `PreSignUp` — can validate or block registrations.
  - `DefineAuthChallenge` / `CreateAuthChallenge` / `VerifyAuthChallenge`
    — custom auth flow logic (`ALLOW_CUSTOM_AUTH`).
  Flag the presence of `ALLOW_CUSTOM_AUTH` without reviewing the Lambda
  implementation — the custom challenge logic may be weaker than the
  standard SRP flow.

## Recent AWS features (2024-2026) (moved from SKILL.md)

- **Passwordless authentication with WebAuthn / PASSKEY_DEFAULT (2024-2025):** Cognito now supports passwordless authentication via WebAuthn (passkeys) and PASSKEY_DEFAULT sign-in mode. Auditors should verify that user pools handling sensitive data have passkey-based MFA or passwordless enabled as a stronger alternative to SMS/TOTP MFA.
- **Token revocation and refresh token rotation (2024):** Enhanced token lifecycle management with token revocation API and refresh token rotation. Auditors should verify that `RefreshTokenValidity` is not excessively long and that token revocation is wired into the application's logout flow.
- **Advanced Security Features (ASF) updates (2024):** ASF now includes improved WAF integration and adaptive authentication. Auditors should verify that `AdvancedSecurityMode` is set to `ENFORCED` (not `AUDIT`) for production pools — AUDIT mode only logs threats without blocking.
- **Hosted UI custom domain SNI:** Enhanced custom domain support for the hosted UI. No new audit-surface fields, but auditors should verify that custom domains have valid ACM certificates and TLS configuration.

