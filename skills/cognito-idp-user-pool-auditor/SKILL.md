---
name: cognito-idp-user-pool-auditor
description: 'Audits Amazon Cognito user pools for security posture — MFA enforcement, password policy strength, app-client auth-flow safety (SRP vs password vs admin), OAuth flow exposure (implicit vs code+PKCE), token validity, PreventUserExistenceErrors, Advanced Security Features mode, account recovery, and deletion protection — then provides specific remediation. Use when reviewing a Cognito user pool configuration, auditing app-client auth flows, checking MFA enforcement, validating OAuth settings, or hardening an identity provider before production. Triggers: Cognito, user pool, identity provider, IdP, MFA, MfaConfiguration, password policy, app client, ExplicitAuthFlows, USER_SRP_AUTH, USER_PASSWORD_AUTH, ADMIN_NO_SRP_AUTH, ALLOW_ADMIN_USER_PASSWORD_AUTH, OAuth, implicit flow, code flow, PKCE, PreventUserExistenceErrors, AdvancedSecurityMode, token revocation, RefreshTokenValidity, account takeover, user enumeration, hosted UI, Cognito domain, cognito-idp.'
license: Apache-2.0
compatibility: Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). No AWS CLI required for offline configuration classification. Live-account audits use aws cognito-idp describe-user-pool, describe-user-pool-client, and list-user-pools (AWS CLI v2, SSO or key-based credentials).
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: 'true'
  phase: '2'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: Security
  verdict_shape: INSECURE | WEAK | ADEQUATE | OK
  when_to_use: Reviewing a Cognito user pool configuration before production, auditing app-client auth flows for credential exposure, checking MFA enforcement, validating OAuth settings (implicit vs code flow), hardening an identity provider against account takeover, or checking PreventUserExistenceErrors for user-enumeration risk.
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  keywords: Cognito, user pool, identity provider, IdP, MFA, MfaConfiguration, password policy, app client, ExplicitAuthFlows, USER_SRP_AUTH, USER_PASSWORD_AUTH, ADMIN_NO_SRP_AUTH, ALLOW_ADMIN_USER_PASSWORD_AUTH, OAuth, implicit flow, PKCE, PreventUserExistenceErrors, AdvancedSecurityMode, token revocation, RefreshTokenValidity, account takeover, user enumeration, hosted UI, cognito-idp
  tags: cognito, security, identity, mfa, oauth, auth-flows, user-pool, audit, compliance
  dependencies: aws-orchestrator
---

# Cognito User Pool Auditor

## Mindset

Classify a Cognito user pool configuration against identity-security best
practices and provide specific remediation. The goal is not just "is MFA on?"
— it is to evaluate the **complete attack surface** of the identity layer:
how users authenticate (SRP vs password vs admin), how tokens are issued
(code vs implicit), whether user enumeration is possible, whether adaptive
threat protection is active, and whether the password policy creates a
meaningful barrier.

A pool with `MfaConfiguration: ON` looks secure until you notice the app
client exposes `ALLOW_ADMIN_USER_PASSWORD_AUTH` (bypasses SRP) or the OAuth
flow is `implicit` (tokens leaked via URL fragment). The classification must
catch both the obvious gaps (MFA OFF) and the subtle misconfigurations that
undermine an otherwise hardened pool.

## Quick reference

If MFA is OFF and the password policy is weak, the pool is INSECURE. If OAuth
implicit flow is enabled, the pool is INSECURE regardless of other settings.
If `PreventUserExistenceErrors` is `LEGACY`, the pool is INSECURE (user
enumeration). If MFA is OPTIONAL, the pool is WEAK (users can skip MFA). If
MFA is ON but AdvancedSecurityMode is OFF or AUDIT (not ENFORCED), the pool
is ADEQUATE at best. See the steps below for the full ordered decision tree.

## Process — Classification logic (apply in order)

The classification evaluates four control layers in the order they gate an
attacker. The first matching severity wins — a single critical deficiency
makes the entire pool INSECURE, regardless of how well other layers are
configured. This mirrors how Cognito evaluates a sign-in request: the auth
flow is checked first (what credential path is open), then MFA (is a second
factor required), then the password policy (how hard is the first factor to
crack), then adaptive controls (does ASF block suspicious patterns).

### Step 0: Validate input

If the pool configuration is missing required fields (`MfaConfiguration` or
`Policies.PasswordPolicy`), output:

```text
USER POOL: <name>
VERDICT: ERROR
REASON: Configuration is incomplete — MfaConfiguration or PasswordPolicy missing.
REMEDIATION: Run aws cognito-idp describe-user-pool --user-pool-id <id> and provide the full output.
```

Do not attempt classification on incomplete input.

### Step 1: INSECURE — critical deficiencies (any one match → INSECURE)

Evaluate each condition below. If **any one** matches, the pool is INSECURE
with **CRITICAL** risk. These are single-point-of-failure controls — one
missing control opens a direct path to account compromise or mass credential
exposure.

**1a. MFA OFF + weak password policy.**
`MfaConfiguration` is `OFF` AND the password policy has `MinimumLength` < 8
OR fewer than 2 of the 4 `Require*` flags set to true. No second factor and a
trivially crackable first factor — the account is protected by a password
that modern GPUs can brute-force in minutes. Cite "Rule 1a: no MFA + weak
password".

**1b. OAuth implicit flow enabled.**
`AllowedOAuthFlows` includes `"implicit"`. The implicit grant type returns
the access token directly in the URL fragment (`#access_token=...`). This
token is accessible via:
- Browser history (persists across sessions).
- The `Referer` header on the callback page (leaked to any third-party
  script or analytics tag on that page).
- Browser extensions with `tabs` or `webRequest` permissions.

OAuth 2.1 (the in-progress consolidation of OAuth 2.0) **removes implicit
flow entirely**. Cite "Rule 1b: OAuth implicit flow — token leakage".

**1c. PreventUserExistenceErrors is LEGACY.**
`PreventUserExistenceErrors` is `"LEGACY"` (or `false` in older pools).
Cognito returns different error messages for non-existent users
(`UserNotFoundException`) vs wrong passwords
(`NotAuthorizedException`). An attacker scripts the login endpoint to
enumerate valid usernames or email addresses, then targets those accounts
with credential stuffing. When set to `ENABLED` (`true`), Cognito returns
the same generic error and runs the full authentication flow even for
non-existent users (preventing timing-based enumeration). Cite "Rule 1c:
user enumeration via legacy error responses".

**1d. Admin auth flow on a public client.**
`ExplicitAuthFlows` includes `"ALLOW_ADMIN_USER_PASSWORD_AUTH"` (or the
legacy name `"ADMIN_NO_SRP_AUTH"`) AND `GenerateSecret` is `false`. The
admin auth flow sends the username and password directly to the
`AdminInitiateAuth` API, bypassing SRP entirely. On a public client (no
secret), this is exploitable by any caller — no server-side credential is
required. Cite "Rule 1d: admin auth flow on public client".

**1e. MFA OFF + AdvancedSecurityMode OFF + no compensating control.**
`MfaConfiguration` is `OFF` AND `UserPoolAddOns.AdvancedSecurityMode` is
`OFF`. Even if the password policy is strong, the pool has zero adaptive
protection — no compromised-credential checking, no impossible-travel
detection, no bot detection. This is the "all eggs in the password basket"
pattern. Cite "Rule 1e: no MFA + no ASF — zero adaptive defense".

**Severity within INSECURE:** all Rule-1 conditions map to **CRITICAL** risk.
A pool that matches Rule 1b (implicit OAuth) or 1d (admin auth on public
client) is the most dangerous — these are directly exploitable from the
client side without any brute-force effort.

### Step 2: WEAK — missing important hardening

If no Step-1 condition matched, evaluate these. If **any one** matches, the
pool is WEAK with **HIGH** risk. These are configurations that do not open an
immediate exploit path but leave the pool vulnerable to targeted attacks.

**2a. MfaConfiguration is OPTIONAL.**
MFA is available but not required. Users can skip enrollment, leaving their
accounts protected by password alone. In practice, most users skip optional
MFA — adoption rates are typically below 20% without enforcement. Cite
"Rule 2a: MFA optional — users can skip".

**2b. MFA OFF but strong password policy + ASF.**
`MfaConfiguration` is `OFF` but `MinimumLength` >= 12 with all 4
`Require*` flags true AND `AdvancedSecurityMode` is `ENFORCED`. This is the
weakest acceptable posture for MFA-off pools — compensating controls (strong
passwords + adaptive protection) reduce but do not eliminate risk. Cite
"Rule 2b: MFA off with compensating controls".

**2c. Password policy at minimum compliance.**
`MinimumLength` is exactly 8 (the NIST SP 800-63B minimum) with fewer than
4 of the complexity flags set, OR `MinimumLength` is >= 8 but
`TemporaryPasswordValidityDays` > 7 (temp passwords valid too long). Cite
"Rule 2c: minimum-compliance password policy".

**2d. USER_PASSWORD_AUTH enabled without SRP.**
`ExplicitAuthFlows` includes `"ALLOW_USER_PASSWORD_AUTH"` but NOT
`"ALLOW_USER_SRP_AUTH"`. The password is sent directly to the API in
plaintext (over TLS, but exposed to the application layer). SRP (Secure
Remote Password) never transmits the password — it uses a zero-knowledge
proof. Without SRP, a compromised API endpoint or a TLS-terminating proxy
can capture passwords. Cite "Rule 2d: non-SRP auth flow".

**2e. Refresh token validity excessive.**
`RefreshTokenValidity` > 30 days (with `TokenValidityUnits.RefreshToken` =
`"days"`). A stolen refresh token remains valid for over a month, allowing
persistent access. Cognito does not natively support refresh token rotation
— shortening validity is the only mitigation. Cite "Rule 2e: long-lived
refresh tokens".

**2f. AdvancedSecurityMode is OFF (or AUDIT) when MFA is ON.**
MFA is enforced but there is no adaptive threat detection. Compromised
credentials (from breaches) will pass MFA if the attacker has the second
factor (via SIM-swap for SMS, or device theft for TOTP). ASF's
compromised-credential detection blocks these. `AUDIT` mode logs suspicious
activity but does not block it — it is monitoring, not protection. Cite
"Rule 2f: ASF not enforced".

**2g. Admin auth flow present (ANY client).**
`ExplicitAuthFlows` includes `"ALLOW_ADMIN_USER_PASSWORD_AUTH"` (or legacy
`"ADMIN_NO_SRP_AUTH"`). This ALWAYS triggers WEAK — regardless of
`GenerateSecret` or other flows present alongside it. The admin auth flow
bypasses SRP and sends the password to the `AdminInitiateAuth` API, which
requires AWS credentials (expanding the attack surface). The presence of
`ALLOW_USER_SRP_AUTH` alongside the admin flow does NOT mitigate this.
Cite "Rule 2g: admin auth flow present".

**2h. OAuth redirect URLs insecure.**
`AllowedOAuthFlows` includes `"code"` (good) but `CallbackURLs` contains an
`http://` URL (not HTTPS) or a wildcard domain (`https://*.example.com`).
HTTP redirects leak the authorization code in transit. Wildcard redirects
allow any subdomain to receive the code — if any subdomain is compromised
or has an open redirect, the code can be intercepted. Cite "Rule 2h:
insecure OAuth redirect".

**Severity within WEAK:** all Rule-2 conditions map to **HIGH** risk. A pool
that matches Rule 2d (non-SRP auth) or 2a (optional MFA) is the most common
real-world weakness.

### Step 3: ADEQUATE — reasonable security with minor gaps

If no Step-2 condition matched on ANY app client, the pool has MFA enforced
with a reasonable password policy and no weak auth flows on any client.
Evaluate whether the remaining controls meet the OK bar. If any gap remains,
the pool is ADEQUATE with **MODERATE** risk.

**3a. AdvancedSecurityMode is AUDIT (not ENFORCED).**
MFA is ON, password policy is strong, but ASF is in AUDIT mode. Suspicious
activity is logged but not blocked. AUDIT is appropriate during a phased
rollout (monitor for false positives before enforcing) but should transition
to ENFORCED within a defined period. Cite "Rule 3a: ASF in audit mode".

**3b. Password policy meets minimum but not maximum.**
`MinimumLength` is 8-11 with all 4 `Require*` flags true. This meets NIST
SP 800-63B minimum but does not provide the 12+ character length that
significantly increases crack resistance. Cite "Rule 3b: adequate password
length".

**3c. Refresh token validity at boundary.**
`RefreshTokenValidity` is exactly 30 days. This is the Cognito default and
is acceptable for most consumer apps, but sensitive applications (financial,
healthcare) should use 1-7 days. Cite "Rule 3c: default refresh token
validity".

**3d. USER_PASSWORD_AUTH alongside SRP.**
`ExplicitAuthFlows` includes both `ALLOW_USER_SRP_AUTH` AND
`ALLOW_USER_PASSWORD_AUTH`. SRP is the primary flow (good), but the
password flow is also available. This is common — some SDKs (older
Amazon Cognito Amplify versions before v6, native mobile SDKs using
direct authentication) require `USER_PASSWORD_AUTH`. Flag it as ADEQUATE
because the SRP path exists, but recommend migrating clients to SRP-only
when feasible. Cite "Rule 3d: password auth alongside SRP".

**3e. MFA is ON with SMS only (no TOTP).**
`MfaConfiguration` is `ON` but `EnabledMfas` includes only `"SMS"`, not
`"SOFTWARE_TOKEN_MFA"`. SMS MFA is vulnerable to SIM-swapping attacks.
TOTP (authenticator apps) is significantly more secure. SMS MFA is still
better than no MFA, but the pool should enable TOTP as well. Cite "Rule
3e: SMS-only MFA — SIM-swap risk".

### Step 4: OK — all controls properly configured

If no Step-3 condition matched, the pool meets all of the following:

- `MfaConfiguration` is `ON` (enforced for all users).
- `EnabledMfas` includes `"SOFTWARE_TOKEN_MFA"` (TOTP available; SMS may
  also be present as fallback).
- `PasswordPolicy.MinimumLength` >= 12 with all 4 `Require*` flags true.
- `UserPoolAddOns.AdvancedSecurityMode` is `ENFORCED`.
- All app clients use `ALLOW_USER_SRP_AUTH` and/or
  `ALLOW_REFRESH_TOKEN_AUTH` only (no `USER_PASSWORD_AUTH`, no admin
  auth flows) — or `USER_PASSWORD_AUTH` is present only on a client that
  has `GenerateSecret: true` AND a documented legacy-SDK justification.
- `PreventUserExistenceErrors` is `ENABLED`.
- `EnableTokenRevocation` is `true`.
- `RefreshTokenValidity` <= 30 days.
- OAuth (if configured) uses `code` flow only with HTTPS callback URLs and
  no wildcard domains.
- `DeletionProtection` is `ACTIVE`.

Cite "Rule 4: all controls met — hardened pool".

### Step 5: Risk-level mapping

**Risk level per verdict (emit exactly one RISK):**

- `INSECURE` → **CRITICAL** — directly exploitable: account takeover, token
  leakage, user enumeration, or credential capture.
- `WEAK` → **HIGH** — not immediately exploitable but vulnerable to targeted
  attacks: optional MFA, non-SRP flows, long-lived tokens, no adaptive
  protection.
- `ADEQUATE` → **MODERATE** — MFA is enforced with reasonable controls, but
  defense-in-depth gaps remain (ASF not enforced, SMS-only MFA, password
  policy at minimum).
- `OK` → **LOW** — all controls properly configured.

### Step 6: Multi-client aggregation

A user pool typically has multiple app clients (e.g., a web client, a mobile
client, a backend service client). Each client has its own
`ExplicitAuthFlows`, `GenerateSecret`, `RefreshTokenValidity`, and OAuth
settings. The pool-level verdict is the **worst** verdict across all app
clients, evaluated on the same INSECURE > WEAK > ADEQUATE > OK scale.

Evaluate each client independently against Steps 1-4, then aggregate:

- If any client is INSECURE, the pool is INSECURE.
- If any client is WEAK (and none is INSECURE), the pool is WEAK.
- If any client is ADEQUATE (and none is WEAK/INSECURE), the pool is ADEQUATE.
- Only if all clients are OK is the pool OK.

Pool-level controls (`MfaConfiguration`, `PasswordPolicy`,
`AdvancedSecurityMode`, `PreventUserExistenceErrors`) are evaluated once and
apply to all clients.

## Auth-flow strength matrix

Moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md) - load on demand (see References below).


## OAuth flow strength matrix

Moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md) - load on demand (see References below).


## Multi-client and edge-case handling

Moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md) - load on demand (see References below).


## Output format (per user pool)

```text
USER POOL: <name>
VERDICT: INSECURE | WEAK | ADEQUATE | OK
REASON: <1-2 sentences citing the specific rule and config>
RISK: CRITICAL | HIGH | MODERATE | LOW
REMEDIATION: <specific action, or "None required" if OK>
```

### Multi-client aggregation example

A pool with two app clients — one hardened, one with admin auth flow:

```text
USER POOL: my-app-pool
VERDICT: WEAK
REASON: Pool-level controls are strong (MFA ON, password policy 12+ chars,
        ASF ENFORCED, PreventUserExistenceErrors ENABLED). However, app client
        'legacy-backend' has ALLOW_ADMIN_USER_PASSWORD_AUTH with GenerateSecret
        true (Rule 2g — admin auth flow on confidential client). Pool verdict
        is the worst client verdict.
RISK: HIGH
REMEDIATION: Evaluate whether the 'legacy-backend' client still needs the
             admin auth flow. If it does, scope it to a dedicated
             infrastructure client with restrictive IAM policies. If it does
             not, remove ALLOW_ADMIN_USER_PASSWORD_AUTH from ExplicitAuthFlows
             and migrate to ALLOW_USER_SRP_AUTH.
```

## Anti-Patterns — NEVER

- NEVER classify a pool with `MfaConfiguration: OFF` as ADEQUATE or OK.
  Without MFA, the pool is at best WEAK (Step 2b — only if password policy
  is strong AND ASF is ENFORCED). MFA is the single most effective control
  against credential stuffing and account takeover. Classifying an MFA-off
  pool as ADEQUATE is a false sense of security.

- NEVER classify a pool with `AllowedOAuthFlows: ["implicit"]` as anything
  other than INSECURE. The implicit flow returns tokens in the URL fragment,
  accessible to any script on the callback page. OAuth 2.1 deprecates it
  entirely. This is not a "style preference" — it is a token-leakage
  vulnerability.

- NEVER treat `PreventUserExistenceErrors: LEGACY` as a minor issue. User
  enumeration is the reconnaissance step that precedes credential stuffing.
  An attacker who knows which email addresses have accounts can target them
  with breached passwords. This is INSECURE.

- NEVER assume `ADMIN_NO_SRP_AUTH` and `ALLOW_ADMIN_USER_PASSWORD_AUTH` are
  different flows. They are the same — `ADMIN_NO_SRP_AUTH` was renamed to
  `ALLOW_ADMIN_USER_PASSWORD_AUTH` in the 2019 API update. Older
  tutorials and Terraform modules still use the legacy name. Treat both
  identically.

- NEVER recommend SMS MFA as the sole MFA method without noting SIM-swap
  risk. SMS interception via SIM-swapping is a well-documented attack
  vector. TOTP (authenticator apps) is significantly more secure. If
  `EnabledMfas` includes only `"SMS"`, flag as ADEQUATE (Rule 3e) — SMS MFA
  is better than no MFA, but TOTP should also be enabled.

- NEVER conflate `AdvancedSecurityMode: AUDIT` with `ENFORCED`. AUDIT mode
  logs suspicious activity (compromised credentials, impossible travel,
  bot detection) but does **not** block it. ENFORCED blocks the request.
  AUDIT is appropriate for a transition period, not as an end state.

- NEVER assume a strong password policy compensates for MFA being OFF.
  Password policies are a speed bump — they increase the cost of brute-force
  attacks. MFA is a wall — it blocks the attack entirely even when the
  password is known (which it often is, from breach datasets). ASF's
  compromised-credential detection is the only control that catches
  breached passwords at sign-in, and it requires `ENFORCED` mode.

- NEVER classify `ALLOW_USER_PASSWORD_AUTH` as equivalent to
  `ALLOW_USER_SRP_AUTH`. SRP never transmits the password — it uses a
  zero-knowledge proof. `USER_PASSWORD_AUTH` sends the password to the
  API. While TLS protects the transport, the password is exposed to the
  application layer (API Gateway, WAF rules, access logs). If SRP is
  available for the client SDK, `USER_PASSWORD_AUTH` should be removed.

- NEVER ignore `RefreshTokenValidity`. A refresh token with 365-day
  validity means a stolen token grants access for a year. Cognito does not
  support refresh token rotation (the OAuth 2.0 RFC 6749 best practice) —
  shortening validity is the only mitigation. Check `TokenValidityUnits` to
  confirm the unit is `days`, not `hours`.

- NEVER treat `RefreshTokenValidity` > 30 days with `EnableTokenRevocation:
  false` as merely a minor gap. This combination is the worst-case token-
  theft scenario: the token is long-lived AND cannot be revoked. A stolen
  refresh token grants persistent access until natural expiry with no
  remediation path short of disabling the app client (which invalidates
  ALL users' tokens). Always recommend enabling token revocation before
  shortening refresh token validity.

- NEVER recommend `client_credentials` OAuth flow for user-authentication
  clients. `client_credentials` is machine-to-machine (service-to-service)
  authentication with no user context. If a user-facing app client has only
  `client_credentials`, the configuration is broken.

- NEVER modify MFA configuration (`OFF` to `ON`) without warning about user
  lockout. Changing `MfaConfiguration` to `ON` immediately requires all
  users to have an MFA factor enrolled. Users without an enrolled factor
  will be unable to sign in. Always recommend a phased rollout:
  `OPTIONAL` first (with communication), then `ON` after adoption metrics
  confirm enrollment.

- NEVER assume `DeletionProtection: ACTIVE` protects against attackers.
  Deletion protection prevents accidental pool deletion (operational safety),
  not malicious deletion — an attacker with sufficient IAM permissions can
  disable it first. It is defense-in-depth for operations, not a security
  control against compromise.

- NEVER recommend deleting or recreating a user pool as a remediation step.
  Pool deletion is irreversible and destroys all user accounts, attributes,
  MFA enrollments, and group memberships. Always use `update-user-pool` and
  `update-user-pool-client` for remediation. If the pool must be rebuilt
  (e.g., region migration), export users first via `list-users` and plan a
  parallel-run migration — never delete and recreate as a quick fix.

- NEVER recommend removing `ALLOW_USER_PASSWORD_AUTH` without confirming the
  client SDK supports SRP. Older Amazon Cognito Amplify SDKs (before v6),
  some native iOS/Android integrations, and custom API callers may depend on
  `USER_PASSWORD_AUTH`. Removing it will break those clients. Test the
  migration in a staging environment first.

## Pre-flight safety checks (run before any remediation CLI)

Moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md) - load on demand (see References below).


## Remediation guidance

Moved verbatim to [references/error-handling.md](references/error-handling.md) - load on demand (see References below).


## Recent AWS features (2024-2026)

Moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md) - load on demand (see References below).


## References

See the AWS Cognito Identity Provider documentation for:
- `describe-user-pool` / `update-user-pool` CLI reference.
- `describe-user-pool-client` / `update-user-pool-client` CLI reference.
- User pool auth flows (SRP, password, admin, custom).
- OAuth scopes and flows in the Hosted UI.
- Advanced Security Features (ASF) modes and capabilities.
- NIST SP 800-63B (password guidance) and OAuth 2.1 (implicit flow
  deprecation).

## References (load on demand)

- [references/advanced-patterns.md](references/advanced-patterns.md) - auth-flow / OAuth strength matrices, multi-client edge cases, recent AWS features
- [references/diagnostic-commands.md](references/diagnostic-commands.md) - pre-flight safety checks before remediation CLIs
- [references/error-handling.md](references/error-handling.md) - remediation guidance per risk tier

## Domain

AWS CloudOps / Cognito Identity Security & Compliance.

## AWS documentation

- **Service documentation** — [Amazon Cognito Developer Guide](https://docs.aws.amazon.com/cognito/latest/developerguide/what-is-amazon-cognito.html)
- **Security** — [Security in Amazon Cognito](https://docs.aws.amazon.com/cognito/latest/developerguide/security.html)
- **API reference** — [Amazon Cognito Identity Provider API Reference](https://docs.aws.amazon.com/cognito-user-identity-pools/latest/APIReference/)
- **CLI reference** — [AWS CLI Command Reference: cognito-idp](https://docs.aws.amazon.com/cli/latest/reference/cognito-idp/)
- **Blog: Passwordless auth with WebAuthn** — https://aws.amazon.com/blogs/security/introducing-passwordless-authentication-with-webauthn-for-amazon-cognito/
