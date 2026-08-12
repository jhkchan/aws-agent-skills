---
name: cognito-auth-troubleshooter
description: >-
  Diagnoses Amazon Cognito authentication failures through a twelve-category
  diagnostic tree: User Pool sign-in errors (wrong app client, wrong auth
  flow, client secret mismatch on PUBLIC clients), token refresh failures
  (refresh token expired, token revocation, JWKS mismatch), hosted UI
  redirect mismatch (callback URL must match exactly), custom attribute
  write permissions (writable vs readable attributes), pre-token-generation
  Lambda trigger errors, identity pool (federated identities) role assumption
  failures (unauthenticated role trust policy must allow cognito-identity),
  social provider (Google/Facebook/Apple) misconfiguration, SAML provider
  certificate mismatch, MFA setup and bypass issues, password policy
  violations, account recovery flow errors, custom sender Lambda trigger
  errors, domain prefix conflicts, and TLS certificate issues. Walks symptoms
  to a verified root cause with evidence-backed probes; emits
  ROOT_CAUSE_IDENTIFIED or INSUFFICIENT_DATA.
version: 0.1.0
author: Jacky Chan — AWS Community Builder
license: Apache-2.0
compatibility: Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). Offline symptom classification works from pasted error messages and user-pool configuration. Live-account diagnosis uses aws cognito-idp describe-user-pool, describe-user-pool-client, describe-identity-pool, get-identity-pool-roles, list-user-pools, list-user-pool-clients, aws lambda get-function / get-policy (for triggers), aws iam simulate-principal-policy, aws cloudtrail lookup-events, aws logs filter-log-events, and dig / nslookup for domain verification (AWS CLI v2, SSO or key-based credentials).
keywords:
- Cognito
- User Pool
- Identity Pool
- authentication
- authorization
- token refresh
- access token
- ID token
- refresh token
- JWT
- JWKS
- hosted UI
- callback URL
- redirect URI
- app client
- client secret
- PUBLIC client
- CONFIDENTIAL client
- auth flow
- ALLOW_USER_PASSWORD_AUTH
- ALLOW_USER_SRP_AUTH
- ALLOW_REFRESH_TOKEN_AUTH
- custom attributes
- pre-token-generation
- Lambda trigger
- identity pool
- federated identities
- unauthenticated role
- trust policy
- cognito-identity
- social provider
- Google
- Facebook
- SignInWithApple
- SAML
- certificate mismatch
- MFA
- TOTP
- SMS MFA
- password policy
- account recovery
- custom sender
- domain prefix
- TLS certificate
- troubleshooting
tags:
- cognito
- security
- troubleshooting
- authentication
- user-pool
- identity-pool
- hosted-ui
- jwt
- saml
- mfa
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: true
  phase: 2
  supports_pipeline: true
  entry_point: false
  family: Security
  task_type: troubleshoot
  skill_class: capability
  lifecycle_status: active
  verdict_shape: ROOT_CAUSE_IDENTIFIED | INSUFFICIENT_DATA
  when_to_use: Diagnosing a Cognito authentication failure (sign-in error, token refresh failure, hosted UI redirect mismatch, social or SAML provider error, MFA setup or bypass, identity pool role assumption failure, pre-token-generation Lambda error, domain prefix conflict, TLS error), walking a symptom to the failed layer with verify and fix commands, validating why a user cannot authenticate, or triaging a "users cannot log in" page where the root cause may be app client config, auth flow, token lifecycle, hosted UI, provider, trigger Lambda, or identity pool role trust — not necessarily the application code.
  when_not_to_use: Application-level session management beyond Cognito token exchange (use the application framework's auth docs), API Gateway custom authorizer debugging (use apigateway-http-troubleshooter), root-cause analysis of the user's device or browser (use browser developer tools and device logs), or IAM policy authoring for the authenticated/unauthenticated roles (use iam-least-privilege-advisor). This skill diagnoses Cognito authentication-time failures; it does not audit steady-state security posture or tune application session logic.
  activation_triggers:
  - Cognito authentication failed
  - Cognito NotAuthorizedException
  - Cognito UserLambdaValidationException
  - Cognito InvalidParameterException
  - Cognito redirect mismatch
  - Cognito hosted UI callback URL
  - Cognito token refresh failed
  - Cognito refresh token expired
  - Cognito InvalidGrantException
  - Cognito pre-token-generation Lambda error
  - Cognito identity pool role assumption
  - Cognito unauthenticated role
  - cognito-identity amazonaws com
  - Cognito social provider Google
  - Cognito Facebook login
  - Cognito SignInWithApple
  - Cognito SAML provider
  - Cognito SAML certificate
  - Cognito MFA setup failed
  - Cognito MFA bypass
  - Cognito password policy
  - Cognito custom attributes
  - Cognito domain prefix
  - Cognito TLS certificate
  - troubleshoot Cognito authentication
  invocation_schema: 'Input: either (a) a symptom description (error message, observed behaviour, "users cannot log in", "token refresh returns InvalidGrantException"), optionally paired with the User Pool / Identity Pool configuration and recent CloudWatch logs, OR (b) a UserPoolId / IdentityPoolId plus client context (AppClientId, auth flow, provider name, observed error) for live-account diagnosis. Output: a deterministic TARGET/VERDICT/REASON/LAYER/EVIDENCE/REMEDIATION block where VERDICT ∈ {ROOT_CAUSE_IDENTIFIED, INSUFFICIENT_DATA} and LAYER ∈ {APP_CLIENT_CONFIG, APP_CLIENT_SECRET, AUTH_FLOW, TOKEN_REFRESH, TOKEN_REVOCATION, HOSTED_UI_REDIRECT, CUSTOM_ATTRIBUTE, PRE_TOKEN_GEN_LAMBDA, IDENTITY_POOL_ROLE, IDENTITY_POOL_TRUST, SOCIAL_PROVIDER, SOCIAL_REDIRECT, SAML_PROVIDER, SAML_CERTIFICATE, MFA_CONFIG, MFA_TOTP, MFA_SMS, PASSWORD_POLICY, ACCOUNT_RECOVERY, CUSTOM_SENDER_LAMBDA, DOMAIN_PREFIX, TLS_CERTIFICATE, UNKNOWN}.'
  invocation_example: "# Minimal valid input (offline symptom classification):\nSymptom: \"Users report 'redirect_mismatch' error after entering credentials\non the Cognito hosted UI. The callback URL in the browser bar shows\nhttps://app.example.com/auth/callback but the app client is configured\nwith https://app.example.com/callback.\"\nUserPoolId: us-east-1_AbCdEf123\nAppClientId: 1ab2cd3ef4gh5ij6lmn7opq8rs\nAuthFlow: code grant (hosted UI)\nDomain: auth.example.com (Cognito domain prefix)\nHostedUI callback URLs: https://app.example.com/callback\nExpected callback (from app config): https://app.example.com/auth/callback"
---

# Cognito Auth Troubleshooter

## Quick start

- **Symptom -> layer map (first plausible match drives the first probe):**
  `NotAuthorizedException` on sign-in -> APP_CLIENT_CONFIG / AUTH_FLOW;
  `redirect_mismatch` / `invalid_redirect_uri` -> HOSTED_UI_REDIRECT;
  `InvalidGrantException` on refresh -> TOKEN_REFRESH / TOKEN_REVOCATION;
  `UserLambdaValidationException` on sign-in -> PRE_TOKEN_GEN_LAMBDA;
  social provider button fails -> SOCIAL_PROVIDER / SOCIAL_REDIRECT;
  SAML login loops or fails -> SAML_PROVIDER / SAML_CERTIFICATE;
  MFA code rejected -> MFA_CONFIG / MFA_TOTP / MFA_SMS;
  password rejected on signup/reset -> PASSWORD_POLICY;
  identity pool `NotAuthorizedException` / `AccessDenied` ->
  IDENTITY_POOL_ROLE / IDENTITY_POOL_TRUST;
  custom attribute write fails -> CUSTOM_ATTRIBUTE;
  domain prefix collision -> DOMAIN_PREFIX;
  TLS / certificate error on auth domain -> TLS_CERTIFICATE.
- **Always verify with a probe, never guess.** Each layer has a single
  command that proves or disproves it. A ROOT_CAUSE_IDENTIFIED verdict
  requires positive evidence — a failing probe that matches the symptom
  — not a process of elimination that "must be the client secret."
- **App client secret vs no-secret is the #1 misdiagnosis.** A client
  created with `GenerateClientSecret: true` is a CONFIDENTIAL client and
  requires the secret in every token exchange. A client created with
  `GenerateClientSecret: false` is a PUBLIC client (used by SPAs and
  mobile apps) and must NOT send a secret. Mixing these up produces
  `UnauthorizedException` on every token exchange. Check
  `describe-user-pool-client` output for `ClientSecret` presence before
  anything else.
- **Hosted UI callback URL must match exactly.** Scheme, host, port,
  and path must all match. `https://app.example.com/callback` is NOT
  the same as `https://app.example.com/callback/` or
  `http://app.example.com/callback`. Trailing slashes, http vs https,
  and case sensitivity are the three most common mismatch causes.
- **Identity pool unauthenticated role trust policy must allow
  `cognito-identity.amazonaws.com` as the principal with the
  `sts:AssumeRoleWithWebIdentity` action.** If the trust policy is
  missing or references the wrong identity pool ID in the condition,
  `GetCredentialsForIdentity` returns `NotAuthorizedException` even
  though the authenticated role works fine.
- **INSUFFICIENT_DATA for AWS-side incidents.** A regional Cognito
  outage is not customer-fixable — escalate to AWS Support and surface
  the AWS Health event ARN.

## Mindset

A failing Cognito authentication flow is usually a configuration
mismatch wearing an "auth is broken" costume. The application code is
fine in the majority of cases; the broken thing is the app client
config, the hosted UI callback list, the auth flow allowed list, the
identity pool role trust policy, the provider configuration, or a
Lambda trigger throwing an error. Treat the application code as innocent
until the Cognito configuration, provider wiring, and trigger Lambdas
are proven correct. Senior identity engineers do not start by reading
the application's auth handler; they start with
`describe-user-pool-client` and the most recent CloudWatch log stream
for the trigger Lambda, and only open the handler once config and
triggers are confirmed correct.

## Philosophy

Four behaviours separate a senior Cognito engineer from a generalist:

- **The error type drives the diagnostic order.** A
  `NotAuthorizedException` with `error: invalid_grant` tells you the
  token exchange failed — that is an app-client or auth-flow problem.
  A `redirect_mismatch` error tells you the hosted UI callback URL
  does not match — that is a configuration mismatch, not a code bug. A
  `UserLambdaValidationException` tells you a Lambda trigger threw —
  that is a trigger problem, not a Cognito config problem. Routing the
  symptom to the wrong layer is the #1 source of wasted cycles in
  Cognito incidents.

- **Cognito has TWO token systems, and they fail differently.** User
  Pools issue JWTs (access, ID, and refresh tokens) that are verified
  locally by the application or API Gateway using the JWKS endpoint.
  Identity Pools exchange User Pool tokens (or social/OIDC/SAML tokens)
  for temporary AWS credentials via STS. A "login works but S3 upload
  fails" pattern is almost always an Identity Pool role / trust policy
  problem, not a User Pool problem. Operators who debug the User Pool
  when the Identity Pool is broken waste hours checking JWTs when the
  real issue is `sts:AssumeRoleWithWebIdentity` in the role trust
  policy.

- **Hosted UI and custom UI have different failure modes.** The hosted
  UI (`https://<domain>.auth.<region>.amazoncognito.com` or a custom
  domain) validates the `redirect_uri` parameter against the app
  client's configured `CallbackURLs` list at the authorization endpoint.
  A custom UI (the application's own login page using the SDK directly)
  does NOT use `redirect_uri` — it uses the SDK's direct auth APIs.
  Operators who debug `redirect_uri` on a custom UI flow are chasing a
  non-issue; the error is elsewhere.

- **Lambda triggers are synchronous and block the auth flow.** If a
  trigger (pre-token-generation, pre-sign-up, post-confirmation, custom
  message, define-auth-challenge, create-auth-challenge, verify-auth-
  challenge) throws an unhandled exception, the entire auth flow fails
  with `UserLambdaValidationException`. The error message in the
  exception often contains the Lambda's exception type and message,
  making CloudWatch Logs the fastest path to root cause.

## Expert heuristic

Five behaviors that a senior identity engineer knows from incident
experience but are not surfaced in the Cognito console:

- **ID token, access token, and identity pool session credentials have
  independent lifecycles, and the application must handle each expiry
  separately.** The access token (default 1 hour) is used for API
  authorization. The ID token (default 1 hour) carries OIDC identity
  claims. The refresh token (default 30 days) mints new access/ID
  tokens. But the identity pool session (temporary AWS credentials)
  has its own lifecycle: STS credentials expire per the role's
  `MaxSessionDuration` (default 1 hour, max 12 hours), independent of
  the Cognito token validity. A common failure: the app refreshes the
  access token at 59 minutes but does not call
  `GetCredentialsForIdentity` to refresh STS credentials — the API
  call fails with expired AWS credentials even though the Cognito
  tokens are fresh.

- **Token revocation via `RevokeToken` is NOT immediate for JWTs
  already issued.** Cognito JWTs are stateless — the access and ID
  tokens are signed JWTs that are valid until their `exp` claim,
  regardless of server-side revocation. `RevokeToken` invalidates the
  REFRESH token (preventing new token issuance), but any access/ID
  token already in the client's possession remains valid until expiry
  (up to 1 hour by default). For immediate revocation, use
  `GlobalSignOut` (invalidates all tokens) AND shorten
  `AccessTokenValidity` to minimize the window. There is no JWT
  blocklist in Cognito — this is a fundamental stateless-JWT
  limitation, not a Cognito bug.

- **The hosted UI `cookie` grant flow stores tokens in a Cognito-
  managed cookie, which has different security properties than the
  `code` grant flow.** The `code` grant flow returns an authorization
  code to the app via redirect; the app exchanges it for tokens
  server-side (tokens never appear in the browser URL). The implicit
  `cookie` flow (used by managed login) stores the access/ID tokens
  directly in a non-HttpOnly cookie
  (`CognitoIdentityServiceProvider.<clientId>.<username>.accessToken`),
  accessible to JavaScript. This is a security trade-off: the cookie
  flow enables seamless SSO across subdomains but exposes tokens to
  XSS. The cookie expiry is tied to the token `exp` claim, not to a
  separate session duration. When diagnosing "token leaks in browser
  dev tools," check whether the app client uses the `cookie` grant
  (managed login) vs `code` grant.

- **The SRP (Secure Remote Password) auth flow requires the client to
  compute a verifier, but Cognito never stores the plaintext password
  — only the verifier.** The flow is: (1) client sends `USER_SRP_AUTH`
  with username and a random `SRP_A` value, (2) Cognito responds with
  `SRP_B` and a salt, (3) client computes `PASSWORD_CLAIM_SIGNATURE`
  using HMAC-SHA256 of the password-derived key with the salt and
  `SRP_A`/`SRP_B`. If the client's SRP implementation uses a different
  hash algorithm or key derivation (e.g., some older SDKs use SHA-1,
  newer ones use SHA-256), the signature mismatch causes
  `NotAuthorizedException` with no diagnostic detail. The AWS SDK and
  Amplify handle this correctly, but custom SRP implementations
  (mobile, non-AWS SDKs) are a common source of silent auth failures.

- **Identity pool credential refresh requires re-calling
  `GetCredentialsForIdentity` with the same identity ID, but the STS
  credentials returned may fail if the underlying Cognito token has
  expired.** The refresh chain is: Cognito access token (1 hr) ->
  `GetCredentialsForIdentity` -> STS credentials (1-12 hrs). If the
  app caches STS credentials for 12 hours but the Cognito access token
  expires at 1 hour, the second `GetCredentialsForIdentity` call fails
  because the access token is expired — even though the STS credentials
  are still valid. Always refresh the Cognito access token (via
  `REFRESH_TOKEN_AUTH`) BEFORE calling `GetCredentialsForIdentity` on
  credential expiry. The identity ID persists across credential
  refreshes; do not create a new identity ID for each refresh.

## Quick reference — symptom triage table

| Symptom phrase / error | Most likely layer | First probe |
|---|---|---|
| `NotAuthorizedException`, `error: invalid_client` | APP_CLIENT_SECRET | `describe-user-pool-client` (ClientSecret present? Client sending secret?) |
| `NotAuthorizedException`, `error: invalid_grant` | TOKEN_REFRESH / AUTH_FLOW | `describe-user-pool-client` (ExplicitAuthFlows), check token expiry |
| `redirect_mismatch`, `invalid_redirect_uri` | HOSTED_UI_REDIRECT | `describe-user-pool-client` (CallbackURLs) vs app config |
| `UserLambdaValidationException` | PRE_TOKEN_GEN_LAMBDA / CUSTOM_SENDER_LAMBDA | CloudWatch Logs for the trigger Lambda |
| `GetCredentialsForIdentity` -> `NotAuthorizedException` | IDENTITY_POOL_ROLE / IDENTITY_POOL_TRUST | `get-identity-pool-roles` + IAM role trust policy |
| Social login button -> blank page or error | SOCIAL_PROVIDER / SOCIAL_REDIRECT | User Pool domain + app client callback + provider redirect URIs |
| SAML login -> `InvalidSAMLRole` or loop | SAML_PROVIDER / SAML_CERTIFICATE | Provider metadata, certificate fingerprint |
| MFA code rejected | MFA_CONFIG / MFA_TOTP / MFA_SMS | User Pool MFA config, user's MFA settings |
| Password rejected on signup/reset | PASSWORD_POLICY | User Pool Policies (password policy) |
| Custom attribute write -> `ResourceNotFoundException` or silent failure | CUSTOM_ATTRIBUTE | `describe-user-pool` (SchemaAttributes, `Mutable` flag) |
| Domain prefix -> `DomainAlreadyExists` | DOMAIN_PREFIX | `describe-user-pool-domain` / `list-user-pool-domains` |
| TLS error on auth domain | TLS_CERTIFICATE | Certificate status, ACM, CloudFront distribution |

## Pre-flight: pool state and gather-info gate

Before running symptom-specific probes, gather the canonical pool
configuration and short-circuit on pool states that mimic authentication
failures. Misclassifying these produces hours of debugging for a problem
that is not an auth problem.

### Account-wide pre-flight commands

```bash
# 1. User Pool configuration (Policies, MfaConfiguration,
#    AdminCreateUserConfig, SchemaAttributes, LambdaConfig, Domain)
aws cognito-idp describe-user-pool \
  --user-pool-id <pool-id> --output json

# 2. App Client configuration (ExplicitAuthFlows, CallbackURLs,
#    LogoutURLs, SupportedIdentityProviders, ClientSecret,
#    RefreshTokenValidity, AccessTokenValidity, IdTokenValidity,
#    AllowedOAuthFlows, AllowedOAuthScopes)
aws cognito-idp describe-user-pool-client \
  --user-pool-id <pool-id> --client-id <client-id> --output json

# 3. Identity Pool configuration + role mappings
aws cognito-identity describe-identity-pool \
  --identity-pool-id <identity-pool-id> --output json

aws cognito-identity get-identity-pool-roles \
  --identity-pool-id <identity-pool-id> --output json

# 4. Trigger Lambda CloudWatch Logs (pre-token-generation, etc.)
aws logs filter-log-events \
  --log-group-name /aws/lambda/<trigger-lambda-name> \
  --start-time $(date -d '-30 minutes' +%s)000 \
  --filter-pattern '"ERROR" OR "Exception" OR "timeout"' \
  --output json

# 5. CloudTrail lookup for Cognito API errors
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=EventSource,AttributeValue=cognito-idp.amazonaws.com \
  --start-time $(date -d '-1 hour' +%s) --end-time $(date +%s) \
  --output json

# 6. AWS Health (regional events)
aws health describe-events --filter eventStatusCodes=OPEN,UPCOMING \
  --region us-east-1 --output json
```

### Pool-state short-circuit

| Configuration field | Effect on diagnosis |
|---|---|
| `UserPool.MfaConfiguration: OFF` but user has `SMS_MFA` or `SOFTWARE_AUTH_MFA` setting | MFA was enabled per-user but pool-level MFA is OFF. The user's MFA setting is stale; clear it via `admin-set-user-mfa-preference`. |
| `UserPool.LambdaConfig.PreTokenGeneration` points at a Lambda that does not exist | Every sign-in fails with `UserLambdaValidationException`. Verify the Lambda ARN resolves. |
| `UserPool.Domain` empty but hosted UI is used | The hosted UI requires a domain prefix or custom domain. Without it, the auth domain returns 404. |
| `UserPoolClient.ClientSecret` empty but client sends `client_secret` | PUBLIC client sending a secret that does not exist. The SDK returns `Unauthorized`. |
| `UserPoolClient.ClientSecret` present but client omits it | CONFIDENTIAL client omitting the secret. The SDK returns `invalid_client`. |

### Alias / app client pre-flight

| Field | Effect |
|---|---|
| `UserPoolClient.ExplicitAuthFlows` does not include `ALLOW_USER_PASSWORD_AUTH` | Direct `AdminInitiateAuth` with `USER_PASSWORD_AUTH` flow fails. Add the flow to the allow list. |
| `UserPoolClient.AllowedOAuthFlows` empty | OAuth/OIDC flows (code grant, implicit) via hosted UI fail. Configure `["code", "implicit"]`. |
| Multiple app clients, caller uses the wrong one | Each app client has its own callback URLs, flows, and scopes. Verify the caller's `client_id` matches the intended app client. |
| `UserPoolClient.PreventUserExistenceErrors: true` | Cognito returns generic `NotAuthorizedException` instead of `UserNotFoundException`. This is a security feature, not a bug. |

If the input is malformed (missing UserPoolId or AppClientId, absent
symptom description, no error string for offline diagnosis), emit:

```text
TARGET: <pool-id / client-id or unknown>
VERDICT: INSUFFICIENT_DATA
REASON: Input is missing required context — at minimum a symptom
  description (the error string or observed behaviour) and the
  UserPoolId or AppClientId.
LAYER: UNKNOWN
EVIDENCE:
  - Missing: <list specific missing fields>
REMEDIATION: Re-prompt the operator for: (1) the exact error string or
  observed symptom, (2) the UserPoolId and AppClientId, (3) the auth
  flow being used (hosted UI code grant, implicit, USER_PASSWORD_AUTH,
  USER_SRP_AUTH, etc.), and (4) for identity pool issues, the
  IdentityPoolId and whether the user is authenticated or
  unauthenticated.
```

## Process — Diagnostic decision tree (apply in symptom order)

The diagnostic tree is symptom-driven. Pick the entry point based on the
observed symptom, then walk the layer-specific probes in order. Each layer
ends with either a positive root-cause confirmation (failing probe that
matches the symptom) or a pass that moves to the next layer. **Never emit
ROOT_CAUSE_IDENTIFIED without a failing probe that matches the symptom.**

### Step 0: Non-obvious behaviours that change diagnosis

These are the operational gotchas a senior identity engineer knows from
incident experience. Each one routes a diagnosis away from the obvious
layer to a less obvious one:

- **User Pool app clients come in two flavours: CONFIDENTIAL and
  PUBLIC.** A CONFIDENTIAL client (the default, `GenerateClientSecret:
  true`) issues a `ClientSecret` that must be included in every
  server-side token exchange. A PUBLIC client (`GenerateClientSecret:
  false`) has no secret and is designed for SPAs and mobile apps. The
  most common misdiagnosis is a PUBLIC client being sent a fabricated
  `client_secret` or a CONFIDENTIAL client being called without one.
  Always check `describe-user-pool-client` for `ClientSecret`
  presence first.

- **`ExplicitAuthFlows` is an allow list, not a default.** Even if the
  SDK call is correct, the flow must be listed in the app client's
  `ExplicitAuthFlows`. A new app client has NO flows enabled by default.
  Operators who "just created the client" and immediately see
  `NotAuthorizedException` on `AdminInitiateAuth` forgot to enable the
  flow. Common flows: `ALLOW_USER_PASSWORD_AUTH` (server-side direct
  login), `ALLOW_USER_SRP_AUTH` (secure remote password),
  `ALLOW_REFRESH_TOKEN_AUTH` (token refresh),
  `ALLOW_ADMIN_USER_PASSWORD_AUTH` (admin-only legacy flow),
  `ALLOW_CUSTOM_AUTH` (custom challenge flow).

- **Token validity durations are independent.** The access token (default
  1 hour / `AccessTokenValidity`), ID token (default 1 hour /
  `IdTokenValidity`), and refresh token (default 30 days /
  `RefreshTokenValidity`) expire independently. A "token expires after
  1 hour" report is the access token expiring — the refresh token is
  still valid and can mint a new access token. Operators who "log out
  after 1 hour" are not propagating the refresh-token exchange.

- **Refresh tokens can be revoked server-side.** `RevokeToken` (API) or
  global sign-out (`GlobalSignOut`) invalidates all previously issued
  tokens including refresh tokens. A user whose refresh token "stopped
  working" may have been globally signed out from another device or by
  an admin. `RefreshTokenValidity` is measured from issuance, not from
  last use — a 30-day refresh token issued 31 days ago is expired even
  if the user was active yesterday.

- **The hosted UI `redirect_uri` is validated at the authorization
  endpoint, not at the token endpoint.** The `redirect_uri` in the
  initial `/oauth2/authorize` call must match a `CallbackURLs` entry
  exactly. The `redirect_uri` in the subsequent `/oauth2/token` call
  must ALSO match the same value used in the authorize call. A mismatch
  at either step produces `redirect_mismatch`.

- **Custom attributes have a `Mutable` flag.** A custom attribute with
  `Mutable: false` can be set only at sign-up time; subsequent
  `UpdateUserAttributes` or `AdminUpdateUserAttributes` calls silently
  fail or return `ResourceNotFoundException`. Operators who "cannot
  update a custom field" are hitting the immutability flag.

- **Pre-token-generation Lambda can modify claims but not add arbitrary
  ones.** The trigger can add to `claimsToAddOrOverride` and
  `claimsToSuppress`, but the total response size is capped at 100 KB.
  A trigger that exceeds the cap causes `UserLambdaValidationException`
  on every sign-in.

- **Identity Pool role assumption requires the trust policy to name
  `cognito-identity.amazonaws.com` with `sts:AssumeRoleWithWebIdentity`,
  and the condition must match the identity pool ID.** The unauthenticated
  role additionally requires the `cognito-identity.amazonaws.com:aud`
  condition matching the identity pool ID and the `cognito-identity.amazonaws.com:amr`
  condition containing `unauth`. A trust policy that references the wrong
  identity pool ID or omits the `amr` condition for unauthenticated
  access causes `GetCredentialsForIdentity` to return
  `NotAuthorizedException`.

- **SAML providers require metadata XML with a valid signing certificate.
  Cognito validates the certificate fingerprint at login time.** If the
  IdP rotates its signing certificate and the metadata in Cognito is not
  updated, every SAML login fails with `SAMLResponseDoesNotMatch` or
  `InvalidSAMLRole`. The fix is to re-import the IdP metadata.

- **Social provider (Google/Facebook/Apple) login has THREE redirect
  URIs that must be consistent:** (1) the provider's authorized
  redirect URI (e.g., in Google Cloud Console) must point at the Cognito
  User Pool domain, (2) the Cognito app client's `CallbackURLs` must
  include the application's callback, and (3) the Cognito provider
  config's `ProviderDetails.authorized_scope` must match the scopes
  configured at the provider. A mismatch at any of the three causes the
  social login to fail silently (blank page) or with a provider-side
  error.

- **Cognito domain prefix is globally unique within a region.** If
  another account (or another pool) already registered the prefix, the
  domain creation fails with `DomainAlreadyExistsException`. Custom
  domains (via ACM certificate + CloudFront) bypass the prefix collision
  but require DNS validation.

- **MFA verification can be TOTP or SMS.** If `MfaConfiguration:
  ON` or `OPTIONAL` and the user has `PreferredMfaSetting: SOFTWARE_TOKEN_MFA`,
  Cognito expects a TOTP code. If `SMS_MFA` is the active setting,
  Cognito sends an SMS via SNS. A user who "switched phones" and lost
  the TOTP seed needs `admin-set-user-mfa-preference` to reset. SMS
  delivery failures route to SNS logs, not Cognito logs.

- **Account recovery flows (forgot password, forgot username) are
  rate-limited.** Cognito limits `ForgotPassword` to a small number of
  attempts per user per time window. A user who "keeps clicking resend"
  may be rate-limited and not receiving emails. Check
  `AccountRecoverySetting` in the pool config for the recovery
  mechanism (email, phone, or both).

### Step 1: Symptom entry — pick the diagnostic branch

Map the symptom to a branch and jump to that branch's section. If the
symptom matches none of the categories, route to Step 13 (INSUFFICIENT_DATA).

| Symptom | Branch |
|---|---|
| `NotAuthorizedException` on sign-in, `invalid_client` | Step 2 — App client |
| `NotAuthorizedException` on sign-in, `invalid_grant` / wrong flow | Step 3 — Auth flow |
| `redirect_mismatch` / `invalid_redirect_uri` | Step 4 — Hosted UI redirect |
| `InvalidGrantException` on refresh token exchange | Step 5 — Token refresh |
| `UserLambdaValidationException` on sign-in | Step 6 — Lambda triggers |
| `GetCredentialsForIdentity` -> `NotAuthorizedException` | Step 7 — Identity pool |
| Social login button -> error / blank page | Step 8 — Social provider |
| SAML login -> `SAMLResponseDoesNotMatch` / loop | Step 9 — SAML provider |
| MFA code rejected / cannot set up MFA | Step 10 — MFA |
| Password rejected on signup or reset | Step 11 — Password policy |
| Custom attribute write fails | Step 12 — Custom attribute |
| `DomainAlreadyExistsException` | Step 12b — Domain prefix |
| TLS error on auth domain | Step 12c — TLS certificate |
| None of the above | Step 13 — INSUFFICIENT_DATA |

### Step 2: App client secret — CONFIDENTIAL vs PUBLIC

Symptom: `NotAuthorizedException` with `error: invalid_client` or a
generic "authentication failed" on the very first API call. The error
fires before any user credentials are validated, because the client
itself is not authenticated.

```bash
aws cognito-idp describe-user-pool-client \
  --user-pool-id <pool-id> --client-id <client-id> --output json | \
  jq '{ClientId, ClientSecret: (.ClientSecret != null), ExplicitAuthFlows, AllowedOAuthFlows}'
```

Key checks:

| Condition | Diagnosis |
|---|---|
| `ClientSecret` present (non-null) but client does not send it | CONFIDENTIAL client used as PUBLIC. Fix: include the secret in the token exchange, or recreate the client with `GenerateClientSecret: false`. |
| `ClientSecret` absent (null) but client sends a fabricated secret | PUBLIC client sent a secret. Fix: remove the `client_secret` parameter from the SDK call. |
| `ClientSecret` present and client sends it, but value is wrong | Stale secret (rotated or recreated). Fix: retrieve the current secret via `describe-user-pool-client` and update the application config. |

**Verdict:** ROOT_CAUSE_IDENTIFIED, `LAYER: APP_CLIENT_SECRET`. Fix:
either align the client type with the usage (PUBLIC or CONFIDENTIAL)
or ensure the correct secret value is used.

### Step 3: Auth flow — wrong or missing flow

Symptom: `NotAuthorizedException` with `error: invalid_grant` or a
flow-specific error on `InitiateAuth` / `AdminInitiateAuth`.

```bash
aws cognito-idp describe-user-pool-client \
  --user-pool-id <pool-id> --client-id <client-id> --output json | \
  jq '.ExplicitAuthFlows'
```

Common flow errors:

| SDK call | Required `ExplicitAuthFlows` entry | Error if missing |
|---|---|---|
| `AdminInitiateAuth` with `AuthFlow: ADMIN_USER_PASSWORD_AUTH` | `ALLOW_ADMIN_USER_PASSWORD_AUTH` | `NotAuthorizedException: Invalid authentication flow` |
| `InitiateAuth` with `AuthFlow: USER_PASSWORD_AUTH` | `ALLOW_USER_PASSWORD_AUTH` | `NotAuthorizedException: Invalid authentication flow` |
| `InitiateAuth` with `AuthFlow: USER_SRP_AUTH` | `ALLOW_USER_SRP_AUTH` | `NotAuthorizedException: Invalid authentication flow` |
| `InitiateAuth` with `AuthFlow: REFRESH_TOKEN_AUTH` | `ALLOW_REFRESH_TOKEN_AUTH` | `NotAuthorizedException: Invalid authentication flow` |
| `InitiateAuth` with `AuthFlow: CUSTOM_AUTH` | `ALLOW_CUSTOM_AUTH` | `NotAuthorizedException: Invalid authentication flow` |

**Verdict:** ROOT_CAUSE_IDENTIFIED, `LAYER: AUTH_FLOW`. Fix: add the
required flow to `ExplicitAuthFlows` via
`update-user-pool-client --explicit-auth-flows`.

### Step 4: Hosted UI redirect mismatch

Symptom: `redirect_mismatch` or `invalid_redirect_uri` from the hosted
UI `/oauth2/authorize` endpoint. The browser URL shows the Cognito
auth domain with an error parameter.

```bash
aws cognito-idp describe-user-pool-client \
  --user-pool-id <pool-id> --client-id <client-id> --output json | \
  jq '.CallbackURLs'
```

Cross-reference each `CallbackURL` against the `redirect_uri` parameter
the application sends:

| Mismatch type | Example | Fix |
|---|---|---|
| Trailing slash | App: `https://app.example.com/callback/` vs Config: `https://app.example.com/callback` | Add the trailing-slash variant to `CallbackURLs` (or remove it from the app) |
| Scheme | App: `http://app.example.com/callback` vs Config: `https://app.example.com/callback` | Match the scheme (prefer HTTPS) |
| Port | App: `https://app.example.com:8443/callback` vs Config: `https://app.example.com/callback` | Add the port to `CallbackURLs` |
| Path | App: `https://app.example.com/auth/callback` vs Config: `https://app.example.com/callback` | Add the exact path |
| Case | App: `https://App.Example.Com/callback` vs Config: `https://app.example.com/callback` | DNS is case-insensitive but Cognito compares case-sensitively; normalise |

**Verdict:** ROOT_CAUSE_IDENTIFIED, `LAYER: HOSTED_UI_REDIRECT`. Fix:
update the app client `CallbackURLs` to include the exact redirect URI
the application sends.

### Step 5: Token refresh failure

Symptom: `InitiateAuth` with `REFRESH_TOKEN_AUTH` returns
`NotAuthorizedException` or `InvalidGrantException`. The user's access
token expired, and the refresh token exchange fails.

```bash
aws cognito-idp describe-user-pool-client \
  --user-pool-id <pool-id> --client-id <client-id> --output json | \
  jq '{RefreshTokenValidity, TokenValidityUnits}'

aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=EventName,AttributeValue=InitiateAuth \
  --start-time $(date -d '-1 hour' +%s) --end-time $(date +%s) \
  --output json | jq '.Events[] | select(.CloudTrailEvent | contains("REFRESH_TOKEN"))'
```

| Cause | Diagnosis | Fix |
|---|---|---|
| Refresh token expired (beyond `RefreshTokenValidity`) | Compare issuance timestamp to current time | Re-authenticate the user; consider raising `RefreshTokenValidity` (1-3650 days). |
| Global sign-out or token revocation | CloudTrail shows `GlobalSignOut` or `RevokeToken` for the user | Re-authenticate; the old refresh token is permanently invalid. |
| Wrong `ClientSecret` on a CONFIDENTIAL client during refresh | `NotAuthorizedException` on refresh specifically | Same as Step 2 — include the correct secret. |
| `RefreshTokenValidity` in the wrong unit | `TokenValidityUnits.RefreshToken` is `days` by default but may be `hours`, `minutes`, or `seconds` | Verify the unit; a value of `30` with unit `hours` is 30 hours, not 30 days. |
| Device tracking / remember-device mismatch | `DeviceConfiguration` enabled but client does not send device key | Configure device tracking or disable `DeviceOnlyRememberedOnUserPrompt`. |

**Verdict:** ROOT_CAUSE_IDENTIFIED, `LAYER: TOKEN_REFRESH` (expiry) or
`TOKEN_REVOCATION` (global sign-out / revoke).

### Step 6: Lambda trigger errors

Symptom: `UserLambdaValidationException` on sign-in, sign-up, forgot
password, or any auth flow. The error message typically contains the
Lambda's exception type and message.

```bash
aws cognito-idp describe-user-pool \
  --user-pool-id <pool-id> --output json | \
  jq '.UserPool.LambdaConfig'

aws logs filter-log-events \
  --log-group-name /aws/lambda/<trigger-name> \
  --start-time $(date -d '-30 minutes' +%s)000 \
  --filter-pattern '"ERROR" OR "Exception" OR "Task timed out"' \
  --output json
```

Common trigger failure patterns:

| Trigger | Error | Common cause |
|---|---|---|
| `PreTokenGeneration` | `UserLambdaValidationException` on every sign-in | Lambda throws on malformed event, response exceeds 100 KB, or response shape does not match `{claimsToAddOrOverride, claimsToSuppress}` |
| `PreSignUp` | `UserLambdaValidationException` on sign-up | Lambda does not return `event.response.autoConfirmUser` or returns wrong shape |
| `PostConfirmation` | `UserLambdaValidationException` after confirmation | Lambda times out calling downstream (e.g., DynamoDB, SES) |
| `CustomMessage` | `UserLambdaValidationException` on verification email | Lambda returns empty `event.response.emailMessage` or missing `emailSubject` |
| `DefineAuthChallenge` / `CreateAuthChallenge` / `VerifyAuthChallenge` | Custom auth flow fails | State machine logic error in the trigger sequence |
| `CustomSMSSender` / `CustomEmailSender` | `InvalidParameterException` | KMS key missing or Lambda cannot decrypt; Lambda does not return the expected `response.smsMessage` / `response.emailMessage` |

**Verdict:** ROOT_CAUSE_IDENTIFIED, `LAYER: PRE_TOKEN_GEN_LAMBDA` (or
the trigger-specific layer). Fix: address the Lambda error (code fix,
timeout increase, IAM permission for downstream calls).

### Step 7: Identity pool role assumption failure

Symptom: `GetCredentialsForIdentity` returns `NotAuthorizedException`
or `AccessDenied`. The User Pool login succeeded (JWT issued) but the
Identity Pool cannot exchange the token for AWS credentials.

```bash
aws cognito-identity get-identity-pool-roles \
  --identity-pool-id <identity-pool-id> --output json

# Check the role trust policy
ROLE_NAME=$(echo <role-arn> | cut -d/ -f2)
aws iam get-role --role-name <role-name> --output json | \
  jq '.Role.AssumeRolePolicyDocument'
```

Key checks for the trust policy:

| Condition | Expected value |
|---|---|
| `Principal` | `"cognito-identity.amazonaws.com"` |
| `Action` | `"sts:AssumeRoleWithWebIdentity"` (or `"sts:AssumeRoleWithWebIdentity"` in newer policies) |
| `Condition.StringEquals["cognito-identity.amazonaws.com:aud"]` | Must match the Identity Pool ID |
| `Condition.StringEquals["cognito-identity.amazonaws.com:amr"]` (unauth role) | Must contain `"unauth"` |
| `Condition.StringEquals["cognito-identity.amazonaws.com:amr"]` (auth role) | Must contain `"authenticated"` or a provider-specific value |

Common failure patterns:

| Pattern | Cause |
|---|---|
| `aud` condition references a different (old) identity pool ID | Trust policy not updated after pool recreation. Fix: update the condition. |
| `amr` condition missing for unauthenticated role | Unauthenticated access denied. Fix: add `"unauth"` to the `amr` condition. |
| Role does not exist or was deleted | `get-identity-pool-roles` shows a role ARN that IAM cannot find. Fix: recreate the role with the correct trust policy. |
| RoleMapping type is `Token` but provider is not configured | The identity pool does not have the User Pool as a configured provider. Fix: add the Cognito User Pool as an identity provider. |
| `RoleMappings` has no rules and `Roles` is empty | No roles configured at all. Fix: set both `Roles` (auth + unauth) and `RoleMappings`. |

**Verdict:** ROOT_CAUSE_IDENTIFIED, `LAYER: IDENTITY_POOL_TRUST` (trust
policy) or `IDENTITY_POOL_ROLE` (role missing or misconfigured).

### Step 8: Social provider misconfiguration

Symptom: clicking the "Login with Google" (or Facebook / Apple) button
on the hosted UI results in a blank page, a provider-side error, or a
redirect to Cognito with an error parameter.

```bash
aws cognito-idp describe-identity-provider \
  --user-pool-id <pool-id> --provider-name Google --output json

aws cognito-idp describe-user-pool-client \
  --user-pool-id <pool-id> --client-id <client-id> --output json | \
  jq '.SupportedIdentityProviders'
```

Three redirect URI consistency checks:

| Check | Expected value |
|---|---|
| Provider authorized redirect URI (Google Console, Facebook App, Apple) | `https://<user-pool-domain>/oauth2/idpresponse` |
| Cognito app client `CallbackURLs` | The application's callback (e.g., `https://app.example.com/callback`) |
| Cognito provider `ProviderDetails.authorized_scopes` | Must match the scopes configured at the provider |

Common failure patterns:

| Pattern | Cause |
|---|---|
| Blank page after provider login | Provider redirect URI does not point at the Cognito domain. Fix: add `https://<domain>/oauth2/idpresponse` to the provider's authorized redirect URIs. |
| `invalid_request` from provider | Missing or wrong `client_id` / `client_secret` in Cognito provider config. Fix: update provider credentials. |
| Provider login succeeds but Cognito returns error | `attribute_mapping` is wrong — Cognito cannot map the provider's claim to a User Pool attribute. Fix: fix the mapping. |
| `UnsupportedIdentityProvider` | Provider not listed in `SupportedIdentityProviders` for the app client. Fix: add the provider name. |
| Apple: `invalid_grant` | Apple uses short-lived (10-minute) authorization codes. The exchange must happen immediately. A delayed or retried exchange fails. Fix: ensure the application exchanges the code in a single immediate call. |
| Apple: `invalid_client` | Apple requires a `.p8` private key for the `client_secret` JWT generation. A wrong Team ID, Key ID, or private key produces this error. Fix: verify the Apple developer account credentials. |

**Verdict:** ROOT_CAUSE_IDENTIFIED, `LAYER: SOCIAL_PROVIDER` (provider
config) or `SOCIAL_REDIRECT` (redirect URI mismatch).

### Step 9: SAML provider certificate mismatch

Symptom: SAML login returns `SAMLResponseDoesNotMatch`,
`InvalidSAMLRole`, or the login loops between the IdP and Cognito.

```bash
aws cognito-idp describe-identity-provider \
  --user-pool-id <pool-id> --provider-name <saml-provider-name> --output json | \
  jq '.ProviderDetails'

# If using metadata URL, verify it is reachable:
curl -sI <metadata-url> | head -5
```

Key checks:

| Check | Expected |
|---|---|
| `ProviderType` | `SAML` |
| `ProviderDetails.MetadataURL` or `MetadataFile` | URL must be reachable and return valid XML; file must be base64-encoded XML |
| Certificate in metadata | Must match the IdP's current signing certificate; expired or rotated certificates cause `SAMLResponseDoesNotMatch` |
| `attribute_mapping` | Maps SAML attributes (e.g., `email`) to User Pool attributes |
| IdP-side Audience / Entity ID | Must be the Cognito User Pool domain (e.g., `https://<domain>.auth.<region>.amazoncognito.com/saml2/idpresponse`) |
| IdP-side NameID format | Cognito expects `urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress` by default |

Common failure patterns:

| Pattern | Cause |
|---|---|
| `SAMLResponseDoesNotMatch` | Certificate in metadata does not match the signing certificate used by the IdP. Fix: re-import updated metadata. |
| Login loop (IdP -> Cognito -> IdP) | The `RelayState` or `InResponseTo` does not match, or Cognito cannot find the user based on the NameID. Fix: check the NameID format and user lookup attribute. |
| `InvalidSAMLRole` | SAML response references a role ARN that does not exist or is not in the IdP's role mapping. Fix: update the role mapping. |
| Metadata URL unreachable from Cognito | Cognito fetches the metadata at login time. If the URL is internal or rate-limited, logins fail intermittently. Fix: use `MetadataFile` instead of `MetadataURL`. |

**Verdict:** ROOT_CAUSE_IDENTIFIED, `LAYER: SAML_CERTIFICATE` (cert
mismatch) or `SAML_PROVIDER` (metadata / mapping issue).

### Step 10: MFA issues

Symptom: MFA code rejected, user cannot set up TOTP, or SMS MFA code
never arrives.

```bash
aws cognito-idp describe-user-pool \
  --user-pool-id <pool-id> --output json | \
  jq '.UserPool.MfaConfiguration'

# User's MFA preference
aws cognito-idp admin-get-user \
  --user-pool-id <pool-id> --username <username> --output json | \
  jq '.MFAOptions, .PreferredMfaSetting, '.UserMFASettingList''
```

| Pattern | Cause | Fix |
|---|---|---|
| TOTP code rejected but user just set it up | Time skew between the user's device and AWS. TOTP is time-based (30-second windows). | Instruct the user to sync their device clock. |
| `MFAMethodNotFoundException` | User has no MFA method configured but pool requires MFA. | Enrol the user in TOTP or SMS MFA. |
| SMS never arrives | SNS delivery failure. Check SNS SMS sandbox, spending limit, or opt-out. | Check CloudWatch for `SMS_OTS` logs; raise SNS SMS spending limit. |
| Cannot disable MFA | `admin-set-user-mfa-preference` with empty list, but `MfaConfiguration: ON` at pool level re-enforces. | Set pool-level `MfaConfiguration` to `OPTIONAL` or `OFF` if MFA is truly optional. |
| `SoftwareTokenMfaSettings` returns error during setup | `AssociateSoftwareToken` was not called before `VerifySoftwareToken`. | Follow the TOTP enrolment sequence: `AssociateSoftwareToken` -> user scans QR -> `VerifySoftwareToken` -> `SetUserMFAPreference`. |
| User locked out after phone loss | TOTP seed is lost; no bypass available via Cognito console. | Use `admin-set-user-mfa-preference` to disable MFA for the user, then re-enrol. |

**Verdict:** ROOT_CAUSE_IDENTIFIED, `LAYER: MFA_TOTP` / `MFA_SMS` /
`MFA_CONFIG`.

### Step 11: Password policy violations

Symptom: sign-up or password reset fails with
`InvalidPasswordException`.

```bash
aws cognito-idp describe-user-pool \
  --user-pool-id <pool-id> --output json | \
  jq '.UserPool.Policies.PasswordPolicy'
```

Check the password against each policy field:

| Policy field | Default | Check |
|---|---|---|
| `MinimumLength` | 8 | Password length >= MinimumLength |
| `RequireUppercase` | true | At least one A-Z |
| `RequireLowercase` | true | At least one a-z |
| `RequireNumbers` | true | At least one 0-9 |
| `RequireSymbols` | true | At least one symbol (^ $ * . [ ] { } ( ) ? " ! @ # % & / \\ , > < ' : ; | _ ~ \`) |
| `TemporaryPasswordValidityDays` | 7 | Temporary passwords expire; user must set a permanent password within this window |

Common failure patterns:

| Pattern | Cause |
|---|---|
| Password meets all rules but still rejected | The password may be in Cognito's common-passwords list. Try a more complex password. |
| `NotAuthorizedException` on first login | Temporary password expired. Admin must reset via `admin-reset-user-password`. |
| Password reset email link expired | `AccountRecoverySetting` defines verification; the reset code is valid for a limited time (default 1 hour). Re-trigger `ForgotPassword`. |

**Verdict:** ROOT_CAUSE_IDENTIFIED, `LAYER: PASSWORD_POLICY`.

### Step 12: Custom attribute write permissions

Symptom: `admin-update-user-attributes` or `update-user-attributes`
fails silently or returns an error when writing a custom attribute.

```bash
aws cognito-idp describe-user-pool \
  --user-pool-id <pool-id> --output json | \
  jq '.UserPool.SchemaAttributes[] | select(.Name | startswith("custom:"))'
```

Check for each custom attribute:

| Field | Effect |
|---|---|
| `Mutable: false` | Attribute can be set only at sign-up (via `SignUp` or `AdminCreateUser`). Subsequent updates fail. |
| `AttributeDataType: String` with `StringAttributeConstraints` | Value must match min/max length constraints. |
| `DeveloperOnlyAttribute: true` | Attribute can only be read/written with admin credentials (`admin-*` APIs), not user-level APIs. |

**Verdict:** ROOT_CAUSE_IDENTIFIED, `LAYER: CUSTOM_ATTRIBUTE`. Fix: set
`Mutable: true` (requires recreating the attribute in a new pool —
attributes are immutable after creation), or write the attribute only
at sign-up time.

### Step 12b: Domain prefix conflict

Symptom: `DomainAlreadyExistsException` when creating a Cognito domain
or custom domain.

```bash
aws cognito-idp describe-user-pool-domain \
  --domain <domain-prefix> --output json 2>/dev/null

aws cognito-idp list-user-pool-domains \
  --max-results 60 --output json
```

If `describe-user-pool-domain` returns a result for a different user
pool, the prefix is taken. Custom domains (ACM certificate + Route 53
alias) bypass the prefix collision but require the certificate to be
in `us-east-1`.

**Verdict:** ROOT_CAUSE_IDENTIFIED, `LAYER: DOMAIN_PREFIX`.

### Step 12c: TLS certificate issues

Symptom: browser shows TLS warning on the Cognito auth domain; or
custom domain does not resolve.

```bash
# Check ACM certificate status (must be in us-east-1 for CloudFront)
aws acm describe-certificate \
  --certificate-arn <arn> --region us-east-1 --output json | \
  jq '.Certificate.Status, .Certificate.DomainValidationOptions'

# Check the custom domain configuration
aws cognito-idp describe-user-pool \
  --user-pool-id <pool-id> --output json | \
  jq '.UserPool.Domain'
```

| Pattern | Cause |
|---|---|
| `NET::ERR_CERT_COMMON_NAME_INVALID` | Custom domain certificate does not cover the auth domain (SAN mismatch). |
| Certificate `Status: PENDING_VALIDATION` | DNS validation records not added. Add the CNAME from `DomainValidationOptions` to Route 53. |
| Domain does not resolve | CloudFront distribution for the custom domain is still deploying (10-20 minutes). |

**Verdict:** ROOT_CAUSE_IDENTIFIED, `LAYER: TLS_CERTIFICATE`.

### Step 13: INSUFFICIENT_DATA

If none of the above produced a positive root-cause match, OR the symptom
clearly indicates an AWS-side incident (regional Cognito outage),
emit:

- **INSUFFICIENT_DATA** — A specific probe requires operator input. List
  the missing pieces (UserPoolId, AppClientId, auth flow, exact error
  string, trigger Lambda logs, provider config) and the next probe to
  run once the info is available. Optionally surface AWS Health event
  ARN if a regional incident is suspected.

## Output format

```text
TARGET: <pool-id / client-id / provider name>
VERDICT: ROOT_CAUSE_IDENTIFIED | INSUFFICIENT_DATA
REASON: <1-2 sentences naming the failed layer and the failing probe>
LAYER: <APP_CLIENT_CONFIG | APP_CLIENT_SECRET | AUTH_FLOW |
        TOKEN_REFRESH | TOKEN_REVOCATION | HOSTED_UI_REDIRECT |
        CUSTOM_ATTRIBUTE | PRE_TOKEN_GEN_LAMBDA |
        IDENTITY_POOL_ROLE | IDENTITY_POOL_TRUST |
        SOCIAL_PROVIDER | SOCIAL_REDIRECT |
        SAML_PROVIDER | SAML_CERTIFICATE |
        MFA_CONFIG | MFA_TOTP | MFA_SMS |
        PASSWORD_POLICY | ACCOUNT_RECOVERY |
        CUSTOM_SENDER_LAMBDA | DOMAIN_PREFIX |
        TLS_CERTIFICATE | UNKNOWN>
EVIDENCE:
  - <observed symptom — error string or behaviour>
  - <failing probe — command and its output that confirms the cause>
  - <passing probes — layers ruled out>
REMEDIATION:
  1. <specific action with CLI command>
  2. <verification command after the fix>
CONFIRM: Before executing any state-changing CLI, emit and await operator
  approval: "CONFIRM: About to <action> on <pool / client> in <region>.
  Proceed? (yes/no)"
```

### Worked example — Hosted UI redirect mismatch

```text
TARGET: us-east-1_AbCdEf123 / client 1ab2cd3ef4gh5ij6lmn7opq8rs
VERDICT: ROOT_CAUSE_IDENTIFIED
REASON: The application sends redirect_uri=https://app.example.com/auth/callback
  but the app client CallbackURLs lists only
  https://app.example.com/callback. The path /auth/callback is missing
  from the configured callback list (Step 4).
LAYER: HOSTED_UI_REDIRECT
EVIDENCE:
  - Symptom: all users see redirect_mismatch error after entering
    credentials on the hosted UI. The browser address bar shows
    redirect_uri=https://app.example.com/auth/callback.
  - Probe: aws cognito-idp describe-user-pool-client returns
    CallbackURLs: ["https://app.example.com/callback"] — the path
    /auth/callback is absent.
  - Passing: ClientSecret is null (PUBLIC client, no secret mismatch);
    ExplicitAuthFlows includes ALLOW_REFRESH_TOKEN_AUTH and
    ALLOW_USER_SRP_AUTH; no Lambda triggers configured.
REMEDIATION:
  1. Add the correct callback URL to the app client:
     aws cognito-idp update-user-pool-client \
       --user-pool-id us-east-1_AbCdEf123 \
       --client-id 1ab2cd3ef4gh5ij6lmn7opq8rs \
       --callback-urls "https://app.example.com/auth/callback" "https://app.example.com/callback"
  2. Verify by navigating to the hosted UI authorize endpoint with
     redirect_uri=https://app.example.com/auth/callback — the redirect
     should succeed without error.
CONFIRM: Before updating the app client, emit and await:
  "CONFIRM: About to add https://app.example.com/auth/callback to
   CallbackURLs on client 1ab2cd3ef4gh5ij6lmn7opq8rs. Proceed? (yes/no)"
```

### Worked example — Identity pool unauthenticated role trust policy

```text
TARGET: identity-pool us-east-1:123456789012:example-pool
VERDICT: ROOT_CAUSE_IDENTIFIED
REASON: GetCredentialsForIdentity returns NotAuthorizedException for
  unauthenticated access. The unauthenticated role's trust policy
  principal is sts.amazonaws.com instead of
  cognito-identity.amazonaws.com, and the aud condition references the
  wrong identity pool ID (Step 7).
LAYER: IDENTITY_POOL_TRUST
EVIDENCE:
  - Symptom: unauthenticated guests cannot access the app; API calls
    return 403. Authenticated users work fine.
  - Probe: aws cognito-identity get-identity-pool-roles returns
    Roles: {UnauthRole: arn:aws:iam::123456789012:role/CognitoUnauthRole}.
    aws iam get-role shows AssumeRolePolicyDocument with Principal:
    {Service: "sts.amazonaws.com"} and condition aud =
    "us-east-1:OLD_POOL_ID".
  - Passing: the authenticated role trust policy is correct (Principal:
    cognito-identity.amazonaws.com, aud matches current pool ID).
REMEDIATION:
  1. Update the unauthenticated role trust policy:
     aws iam update-assume-role-policy \
       --role-name CognitoUnauthRole \
       --policy-document '{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":{"Federated":"cognito-identity.amazonaws.com"},"Action":"sts:AssumeRoleWithWebIdentity","Condition":{"StringEquals":{"cognito-identity.amazonaws.com:aud":"us-east-1:123456789012:example-pool"},"ForAnyValue:StringLike":{"cognito-identity.amazonaws.com:amr":"unauth"}}}]}'
  2. Verify by calling GetCredentialsForIdentity with an unauthenticated
    identity and confirming it returns credentials without error.
CONFIRM: Before updating the trust policy, emit and await:
  "CONFIRM: About to update CognitoUnauthRole trust policy. Proceed?
   (yes/no)"
```

### Worked example — Pre-token-generation Lambda error

```text
TARGET: us-east-1_AbCdEf123 / trigger: pre-token-gen-fn
VERDICT: ROOT_CAUSE_IDENTIFIED
REASON: Every sign-in fails with UserLambdaValidationException. The
  pre-token-generation Lambda throws TypeError: Cannot read property
  'department' of undefined when the IdP claim mapping is missing the
  custom:department attribute (Step 6).
LAYER: PRE_TOKEN_GEN_LAMBDA
EVIDENCE:
  - Symptom: no user can sign in; all return
    UserLambdaValidationException with the Lambda exception message.
  - Probe: aws logs filter-log-events on /aws/lambda/pre-token-gen-fn
    returns "TypeError: Cannot read property 'department' of undefined"
    200 times in the last hour.
  - Passing: User Pool MfaConfiguration is OFF; no SAML or social
    providers configured; app client ExplicitAuthFlows includes
    ALLOW_USER_PASSWORD_AUTH.
REMEDIATION:
  1. Fix the Lambda to handle missing custom attributes gracefully:
     const department = event.request.userAttributes['custom:department'] || 'unknown';
  2. Deploy the updated Lambda function.
  3. Verify by signing in as a test user and confirming the JWT
    contains the department claim.
```

## Anti-Patterns — NEVER

- NEVER declare ROOT_CAUSE_IDENTIFIED without a failing probe that
  matches the symptom. A "process of elimination" diagnosis erodes
  operator trust when the real cause is elsewhere.

- NEVER assume the app client is PUBLIC because the application is a
  SPA. Check `describe-user-pool-client` for `ClientSecret` presence.
  Many SPAs use CONFIDENTIAL clients with a server-side proxy for the
  secret; others are truly PUBLIC. The diagnostic is driven by config,
  not by application type.

- NEVER add a `client_secret` to a PUBLIC client call. The secret does
  not exist; sending a fabricated value produces `Unauthorized`. If the
  client was created without a secret, the SDK must not send one.

- NEVER compare the `redirect_uri` loosely. Scheme, host, port, path,
  and trailing slash must all match exactly. A single character
  difference (including case) produces `redirect_mismatch`.

- NEVER assume the identity pool role trust policy is correct because
  "it worked before." Pool IDs change when pools are recreated; the
  `aud` condition must reference the CURRENT pool ID. Always verify
  the trust policy's `aud` condition against the live pool ID.

- NEVER forget the `amr` condition for the unauthenticated role. The
  trust policy must include
  `"ForAnyValue:StringLike": {"cognito-identity.amazonaws.com:amr": "unauth"}`
  for unauthenticated access. Omitting it silently breaks guest access.

- NEVER assume the pre-token-generation Lambda is correct because the
  code "hasn't changed." If the upstream IdP stopped sending a claim
  that the Lambda reads, the Lambda throws even though the Lambda code
  is unchanged. Always check CloudWatch Logs for the trigger.

- NEVER update a SAML provider's metadata without verifying the
  certificate. If the IdP rotated its signing certificate and the new
  metadata has the correct cert, updating fixes the issue. But if the
  metadata still has the OLD cert, updating is a no-op and the logins
  still fail.

- NEVER use `MfaConfiguration: ON` at pool level and then try to
  disable MFA per-user. Pool-level `ON` enforces MFA for all users.
  To make MFA optional, use `MfaConfiguration: OPTIONAL`.

- NEVER recreate a User Pool to "fix" a config issue without exporting
  users first. Pool recreation changes the Pool ID, invalidating all
  existing JWTs, app client IDs, identity pool mappings, and trigger
  Lambda ARNs. Always attempt to fix the config in place.

- NEVER assume a custom attribute can be updated after sign-up. Check
  the `Mutable` flag. If `Mutable: false`, the attribute is write-once
  at sign-up time. Making it mutable requires creating a new pool with
  the corrected attribute.

- NEVER set `RefreshTokenValidity` without checking
  `TokenValidityUnits.RefreshToken`. A value of `30` could be 30
  seconds, 30 minutes, 30 hours, or 30 days depending on the unit.
  The default unit is `days`.

- NEVER send the `client_secret` in the browser for a PUBLIC client.
  Even if the client has a secret (misconfigured CONFIDENTIAL client
  used by a SPA), the secret should be proxied through a backend, not
  exposed in client-side code.

## Pre-flight safety checks (run before any state-changing CLI)

- **MANDATORY CONFIRMATION GATE.** Before any state-changing operation
  (`update-user-pool-client`, `update-user-pool`, `update-identity-pool`,
  `update-assume-role-policy`, `set-identity-pool-roles`,
  `admin-set-user-mfa-preference`, `admin-reset-user-password`), emit
  and await operator approval. Do NOT execute the CLI until the
  operator confirms.

- **Read-only first.** Every probe in the diagnostic tree is
  read-only (`describe-user-pool`, `describe-user-pool-client`,
  `describe-identity-provider`, `get-identity-pool-roles`,
  `describe-user-pool-domain`, `filter-log-events`,
  `lookup-events`, `get-role`, `describe-certificate`). Do not perform
  state-changing operations as diagnostic probes.

- **`update-user-pool-client`** changes the app client config. Some
  fields (like `CallbackURLs` and `ExplicitAuthFlows`) are safe to
  update; others (like `GenerateClientSecret`) require recreating the
  client. Always confirm before updating.

- **`update-user-pool`** changes the pool-level config (MFA, password
  policy, Lambda triggers). Changes propagate within seconds but affect
  all users immediately. Confirm before applying.

- **`update-assume-role-policy`** on the identity pool role trust policy
  can break ALL authentication if the policy is malformed. Always
  validate the JSON syntax before applying. Use
  `iam simulate-principal-policy` to verify after the change.

- **`admin-reset-user-password`** sends a reset code to the user. Do
  NOT use this as a diagnostic probe; it has user-visible side effects.

- **Bulk remediation batch limit.** If the diagnosis identifies the
  same root cause across multiple app clients or pools, batch
  remediation into groups of at most 5 resources, emit a single
  CONFIRM per batch, and verify between batches.

## Remediation guidance

### For APP_CLIENT_SECRET

```bash
# Recreate the client as PUBLIC (no secret) — requires deleting and recreating
aws cognito-idp delete-user-pool-client \
  --user-pool-id <pool-id> --client-id <client-id> --profile <p>

aws cognito-idp create-user-pool-client \
  --user-pool-id <pool-id> \
  --client-name <name> \
  --no-generate-secret \
  --explicit-auth-flows ALLOW_USER_SRP_AUTH ALLOW_REFRESH_TOKEN_AUTH \
  --callback-urls "https://app.example.com/callback" \
  --profile <p>
```

### For AUTH_FLOW

```bash
aws cognito-idp update-user-pool-client \
  --user-pool-id <pool-id> --client-id <client-id> \
  --explicit-auth-flows ALLOW_USER_PASSWORD_AUTH ALLOW_USER_SRP_AUTH ALLOW_REFRESH_TOKEN_AUTH \
  --profile <p>
```

### For HOSTED_UI_REDIRECT

```bash
aws cognito-idp update-user-pool-client \
  --user-pool-id <pool-id> --client-id <client-id> \
  --callback-urls "https://app.example.com/auth/callback" "https://app.example.com/callback" \
  --profile <p>
```

### For TOKEN_REFRESH

- If expired: re-authenticate the user. Consider raising
  `RefreshTokenValidity` (check `TokenValidityUnits`).
- If revoked: re-authenticate; old refresh tokens are permanently invalid.

```bash
aws cognito-idp update-user-pool-client \
  --user-pool-id <pool-id> --client-id <client-id> \
  --refresh-token-validity 90 \
  --token-validity-units '{"RefreshToken":"days","AccessToken":"hours","IdToken":"hours"}' \
  --profile <p>
```

### For PRE_TOKEN_GEN_LAMBDA / CUSTOM_SENDER_LAMBDA

Fix the Lambda code:
- Add defensive null checks for missing attributes.
- Ensure the response shape matches the Cognito trigger contract.
- Increase the Lambda timeout (Cognito triggers have a 5-second limit).
- Verify IAM permissions for any downstream calls (DynamoDB, SES, SNS, KMS).

### For IDENTITY_POOL_TRUST

```bash
aws iam update-assume-role-policy \
  --role-name <role-name> \
  --policy-document '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Principal": {"Federated": "cognito-identity.amazonaws.com"},
      "Action": "sts:AssumeRoleWithWebIdentity",
      "Condition": {
        "StringEquals": {"cognito-identity.amazonaws.com:aud": "<identity-pool-id>"},
        "ForAnyValue:StringLike": {"cognito-identity.amazonaws.com:amr": "unauth"}
      }
    }]
  }' --profile <p>
```

### For SOCIAL_PROVIDER

- Update the provider's authorized redirect URI to
  `https://<user-pool-domain>/oauth2/idpresponse`.
- Update Cognito provider credentials (`ProviderDetails.client_id` /
  `client_secret`).
- Fix the attribute mapping.

### For SAML_PROVIDER / SAML_CERTIFICATE

```bash
aws cognito-idp update-identity-provider \
  --user-pool-id <pool-id> \
  --provider-name <saml-name> \
  --provider-details MetadataURL=<new-metadata-url> \
  --profile <p>
```

### For MFA_CONFIG

```bash
# Set pool-level MFA to OPTIONAL
aws cognito-idp update-user-pool \
  --user-pool-id <pool-id> \
  --mfa-configuration OPTIONAL \
  --profile <p>

# Reset a user's MFA
aws cognito-idp admin-set-user-mfa-preference \
  --user-pool-id <pool-id> --username <username> \
  --software-token-mfa-settings Enabled=false,PreferredMfa=false \
  --sms-mfa-settings Enabled=false,PreferredMfa=false \
  --profile <p>
```

### For PASSWORD_POLICY

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
  }' --profile <p>
```

### For DOMAIN_PREFIX

- Choose a different prefix (globally unique within region).
- Or use a custom domain (ACM certificate in us-east-1 + CloudFront).

### For TLS_CERTIFICATE

- Request an ACM certificate in us-east-1 for the custom auth domain.
- Add DNS validation CNAME records.
- Wait for `Status: ISSUED`.
- Associate the certificate with the Cognito user pool custom domain.

## Deep reference: Cognito authentication layer model

### Symptom -> layer decision matrix (offline classification)

```
Error string                                   → Layer
NotAuthorizedException + invalid_client         → APP_CLIENT_SECRET
NotAuthorizedException + invalid_grant          → TOKEN_REFRESH / AUTH_FLOW
redirect_mismatch / invalid_redirect_uri        → HOSTED_UI_REDIRECT
UserLambdaValidationException                   → PRE_TOKEN_GEN_LAMBDA / CUSTOM_SENDER_LAMBDA
GetCredentialsForIdentity NotAuthorizedException → IDENTITY_POOL_ROLE / IDENTITY_POOL_TRUST
Social login blank page                         → SOCIAL_PROVIDER / SOCIAL_REDIRECT
SAMLResponseDoesNotMatch                        → SAML_CERTIFICATE
InvalidPasswordException                        → PASSWORD_POLICY
MFAMethodNotFoundException                      → MFA_CONFIG
DomainAlreadyExistsException                    → DOMAIN_PREFIX
NET::ERR_CERT_COMMON_NAME_INVALID               → TLS_CERTIFICATE
```

### Token lifecycle reference

| Token | Default validity | Configurable via | Used for |
|---|---|---|---|
| Access token | 1 hour | `AccessTokenValidity` + `TokenValidityUnits.AccessToken` | API authorization (Bearer token) |
| ID token | 1 hour | `IdTokenValidity` + `TokenValidityUnits.IdToken` | User identity claims (OIDC) |
| Refresh token | 30 days | `RefreshTokenValidity` + `TokenValidityUnits.RefreshToken` | Minting new access/ID tokens without re-auth |

### Auth flow reference

| Flow | SDK API | Use case |
|---|---|---|
| `USER_PASSWORD_AUTH` | `InitiateAuth` | Direct username/password (insecure; use only over TLS) |
| `USER_SRP_AUTH` | `InitiateAuth` + `RespondToAuthChallenge` | Secure Remote Password (no password sent over wire) |
| `ADMIN_USER_PASSWORD_AUTH` | `AdminInitiateAuth` | Server-side admin login (requires `cognito-idp:AdminInitiateAuth`) |
| `REFRESH_TOKEN_AUTH` | `InitiateAuth` | Refresh expired access/ID tokens |
| `CUSTOM_AUTH` | `InitiateAuth` + `RespondToAuthChallenge` | Custom challenge (OTP, CAPTCHA, etc.) |
| `ALLOW_ADMIN_NO_SRP_AUTH` | Deprecated | Use `ADMIN_USER_PASSWORD_AUTH` instead |

### Identity pool role trust policy templates

Authenticated role:

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {"Federated": "cognito-identity.amazonaws.com"},
    "Action": "sts:AssumeRoleWithWebIdentity",
    "Condition": {
      "StringEquals": {"cognito-identity.amazonaws.com:aud": "<identity-pool-id>"},
      "ForAnyValue:StringLike": {"cognito-identity.amazonaws.com:amr": "authenticated"}
    }
  }]
}
```

Unauthenticated role:

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {"Federated": "cognito-identity.amazonaws.com"},
    "Action": "sts:AssumeRoleWithWebIdentity",
    "Condition": {
      "StringEquals": {"cognito-identity.amazonaws.com:aud": "<identity-pool-id>"},
      "ForAnyValue:StringLike": {"cognito-identity.amazonaws.com:amr": "unauth"}
    }
  }]
}
```

### Lambda trigger response size limits

| Trigger | Response size limit | Timeout |
|---|---|---|
| PreTokenGeneration | 100 KB total response | 5 seconds |
| PreSignUp | N/A (boolean response) | 5 seconds |
| PostConfirmation | N/A (void response) | 5 seconds |
| CustomMessage | Email subject + body | 5 seconds |
| DefineAuthChallenge | Challenge response | 5 seconds |
| CustomEmailSender / CustomSMSSender | Encrypted message | 5 seconds |

### Social provider redirect URI matrix

| Provider | Authorized redirect URI (at provider) |
|---|---|
| Google | `https://<user-pool-domain>/oauth2/idpresponse` |
| Facebook | `https://<user-pool-domain>/oauth2/idpresponse` |
| SignInWithApple | `https://<user-pool-domain>/oauth2/idpresponse` |
| LoginWithAmazon | `https://<user-pool-domain>/oauth2/idpresponse` |

## Recent AWS features (2024-2026)

- **Token revocation API (2024):** `RevokeToken` invalidates a specific
  refresh token without global sign-out. Useful for targeted session
  invalidation (e.g., "log out of one device"). Diagnostically, if a
  user's refresh token stops working unexpectedly, check CloudTrail for
  `RevokeToken` or `GlobalSignOut` calls.
- **Improved hosted UI customisation (2024-2025):** Custom CSS and logo
  on the hosted UI. Does not affect auth flow; purely cosmetic.
- **Cognito user pool import (2024):** Bulk user import via CSV and the
  `CreateUserImportJob` API. Imported users may have `UserStatus:
  RESET_REQUIRED` and need a password reset on first login.
- **Managed login (2025):** AWS-hosted OIDC login pages with deeper
  branding and conditional access. Replaces the classic hosted UI for
  new pools; existing pools can opt in. Diagnostically, managed login
  has different error surfaces than the classic hosted UI.
- **Token-based role mapping enhancements (2025):** Identity pools now
  support more granular `RoleMappings` with claim-based rules.
  Diagnostically, a wrong claim path in the rule causes
  `NotAuthorizedException` on `GetCredentialsForIdentity`.

## Domain

AWS CloudOps / Cognito Identity, Authentication and Authorization
Diagnostics, User Pool, Identity Pool, Federated Identities, Lambda
Triggers, and Social / SAML Provider Integration.

## AWS documentation

- **Amazon Cognito Developer Guide — User pools** — https://docs.aws.amazon.com/cognito/latest/developerguide/cognito-user-identity-pools.html
- **Cognito identity pools (federated identities)** — https://docs.aws.amazon.com/cognito/latest/developerguide/cognito-identity.html
- **Cognito hosted UI and managed login** — https://docs.aws.amazon.com/cognito/latest/developerguide/cognito-user-pools-app-integration.html
- **Cognito Lambda triggers** — https://docs.aws.amazon.com/cognito/latest/developerguide/cognito-user-identity-pools-working-with-aws-lambda-triggers.html
- **Adding SAML identity providers** — https://docs.aws.amazon.com/cognito/latest/developerguide/cognito-user-pools-identity-provider.html
- **Adding social identity providers** — https://docs.aws.amazon.com/cognito/latest/developerguide/cognito-user-pools-social-idp.html
- **Cognito token lifecycle** — https://docs.aws.amazon.com/cognito/latest/developerguide/amazon-cognito-user-pools-using-the-id-token.html
- **Cognito MFA** — https://docs.aws.amazon.com/cognito/latest/developerguide/user-pool-settings-mfa.html
- **IAM roles for identity pools** — https://docs.aws.amazon.com/cognito/latest/developerguide/role-based-access-control.html
- **AWS Health** — https://docs.aws.amazon.com/health/latest/ug/
