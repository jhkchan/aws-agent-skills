# Advanced patterns - Cognito Auth Troubleshooter (load on demand)

## Quick start - full symptom map and top misdiagnoses (moved from SKILL.md)

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


## Philosophy - senior-engineer behaviours

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


## Step 0 - Non-obvious behaviours that change diagnosis

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


## Step 8 - Social provider misconfiguration

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


## Step 10 - MFA issues

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


## Step 11 - Password policy violations

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


## Step 12 - Custom attribute write permissions

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


## Step 12b - Domain prefix conflict

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


## Step 12c - TLS certificate issues

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


## Step 13 - INSUFFICIENT_DATA

If none of the above produced a positive root-cause match, OR the symptom
clearly indicates an AWS-side incident (regional Cognito outage),
emit:

- **INSUFFICIENT_DATA** — A specific probe requires operator input. List
  the missing pieces (UserPoolId, AppClientId, auth flow, exact error
  string, trigger Lambda logs, provider config) and the next probe to
  run once the info is available. Optionally surface AWS Health event
  ARN if a regional incident is suspected.


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

