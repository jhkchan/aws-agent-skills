---
name: cognito-auth-troubleshooter
description: 'Diagnoses Amazon Cognito authentication failures through a twelve-category diagnostic tree: User Pool sign-in errors (wrong app client, wrong auth flow, client secret mismatch on PUBLIC clients), token refresh failures (refresh token expired, token revocation, JWKS mismatch), hosted UI redirect mismatch (callback URL must match exactly), custom attribute write permissions (writable vs readable attributes), pre-token-generation Lambda trigger errors, identity pool (federated identities) role assumption failures (unauthenticated role trust policy must allow cognito-identity), social provider (Google/Facebook/Apple) misconfiguration, SAML provider certificate mismatch, MFA setup and bypass issues, password policy violations, account recovery flow errors, custom sender Lambda trigger errors, domain prefix conflicts, and TLS certificate issues. Walks symptoms to a verified root cause with evidence-backed probes; emits ROOT_CAUSE_IDENTIFIED or INSUFFICIENT_DATA.'
license: Apache-2.0
compatibility: Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). Offline symptom classification works from pasted error messages and user-pool configuration. Live-account diagnosis uses aws cognito-idp describe-user-pool, describe-user-pool-client, describe-identity-pool, get-identity-pool-roles, list-user-pools, list-user-pool-clients, aws lambda get-function / get-policy (for triggers), aws iam simulate-principal-policy, aws cloudtrail lookup-events, aws logs...
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: 'true'
  phase: '2'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: Security
  task_type: troubleshoot
  skill_class: capability
  lifecycle_status: active
  verdict_shape: ROOT_CAUSE_IDENTIFIED | INSUFFICIENT_DATA
  when_to_use: Diagnosing a Cognito authentication failure (sign-in error, token refresh failure, hosted UI redirect mismatch, social or SAML provider error, MFA setup or bypass, identity pool role assumption failure, pre-token-generation Lambda error, domain prefix conflict, TLS error), walking a symptom to the failed layer with verify and fix commands, validating why a user cannot authenticate, or triaging a "users cannot log in" page where the root cause may be app client config, auth flow, token lifecycle, hosted UI, provider, trigger Lambda, or identity pool role trust — not necessarily the application code.
  when_not_to_use: Application-level session management beyond Cognito token exchange (use the application framework's auth docs), API Gateway custom authorizer debugging (use apigateway-http-troubleshooter), root-cause analysis of the user's device or browser (use browser developer tools and device logs), or IAM policy authoring for the authenticated/unauthenticated roles (use iam-least-privilege-advisor). This skill diagnoses Cognito authentication-time failures; it does not audit steady-state security posture or tune application session logic.
  activation_triggers: Cognito authentication failed, Cognito NotAuthorizedException, Cognito UserLambdaValidationException, Cognito InvalidParameterException, Cognito redirect mismatch, Cognito hosted UI callback URL, Cognito token refresh failed, Cognito refresh token expired, Cognito InvalidGrantException, Cognito pre-token-generation Lambda error, Cognito identity pool role assumption, Cognito unauthenticated role, cognito-identity amazonaws com, Cognito social provider Google, Cognito Facebook login, Cognito SignInWithApple, Cognito SAML provider, Cognito SAML certificate, Cognito MFA setup failed, Cognito MFA bypass, Cognito password policy, Cognito custom attributes, Cognito domain prefix, Cognito TLS certificate, troubleshoot Cognito authentication
  invocation_schema: 'Input: either (a) a symptom description (error message, observed behaviour, "users cannot log in", "token refresh returns InvalidGrantException"), optionally paired with the User Pool / Identity Pool configuration and recent CloudWatch logs, OR (b) a UserPoolId / IdentityPoolId plus client context (AppClientId, auth flow, provider name, observed error) for live-account diagnosis. Output: a deterministic TARGET/VERDICT/REASON/LAYER/EVIDENCE/REMEDIATION block where VERDICT ∈ {ROOT_CAUSE_IDENTIFIED, INSUFFICIENT_DATA} and LAYER ∈ {APP_CLIENT_CONFIG, APP_CLIENT_SECRET, AUTH_FLOW, TOKEN_REFRESH, TOKEN_REVOCATION, HOSTED_UI_REDIRECT, CUSTOM_ATTRIBUTE, PRE_TOKEN_GEN_LAMBDA, IDENTITY_POOL_ROLE, IDENTITY_POOL_TRUST, SOCIAL_PROVIDER, SOCIAL_REDIRECT, SAML_PROVIDER, SAML_CERTIFICATE, MFA_CONFIG, MFA_TOTP, MFA_SMS, PASSWORD_POLICY, ACCOUNT_RECOVERY, CUSTOM_SENDER_LAMBDA, DOMAIN_PREFIX, TLS_CERTIFICATE, UNKNOWN}.'
  invocation_example: '# Minimal valid input (offline symptom classification):

    Symptom: "Users report ''redirect_mismatch'' error after entering credentials

    on the Cognito hosted UI. The callback URL in the browser bar shows

    https://app.example.com/auth/callback but the app client is configured

    with https://app.example.com/callback."

    UserPoolId: us-east-1_AbCdEf123

    AppClientId: 1ab2cd3ef4gh5ij6lmn7opq8rs

    AuthFlow: code grant (hosted UI)

    Domain: auth.example.com (Cognito domain prefix)

    HostedUI callback URLs: https://app.example.com/callback

    Expected callback (from app config): https://app.example.com/auth/callback'
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  keywords: Cognito, User Pool, Identity Pool, authentication, authorization, token refresh, access token, ID token, refresh token, JWT, JWKS, hosted UI, callback URL, redirect URI, app client, client secret, PUBLIC client, CONFIDENTIAL client, auth flow, ALLOW_USER_PASSWORD_AUTH, ALLOW_USER_SRP_AUTH, ALLOW_REFRESH_TOKEN_AUTH, custom attributes, pre-token-generation, Lambda trigger, identity pool, federated identities, unauthenticated role, trust policy, cognito-identity, social provider, Google, Facebook, SignInWithApple, SAML, certificate mismatch, MFA, TOTP, SMS MFA, password policy, account recovery, custom sender, domain prefix, TLS certificate, troubleshooting
  tags: cognito, security, troubleshooting, authentication, user-pool, identity-pool, hosted-ui, jwt, saml, mfa
---

# Cognito Auth Troubleshooter

## Quick start

Moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md) - load on demand (see References below).

## Mindset

Moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md) - load on demand (see References below).

## Philosophy

Moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md) - load on demand (see References below).

## Expert heuristic

Moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md) - load on demand (see References below).

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

Moved verbatim to [references/cognito-troubleshooting-commands.md](references/cognito-troubleshooting-commands.md) - load on demand (see References below).

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

Moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md) - load on demand (see References below).

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

Moved verbatim to [references/cognito-auth-flow-reference.md](references/cognito-auth-flow-reference.md) - load on demand (see References below).

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

Moved verbatim to [references/cognito-auth-flow-reference.md](references/cognito-auth-flow-reference.md) - load on demand (see References below).

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

Moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md) - load on demand (see References below).

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

Moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md) - load on demand (see References below).

### Step 11: Password policy violations

Moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md) - load on demand (see References below).

### Step 12: Custom attribute write permissions

Moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md) - load on demand (see References below).

### Step 12b: Domain prefix conflict

Moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md) - load on demand (see References below).

### Step 12c: TLS certificate issues

Moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md) - load on demand (see References below).

### Step 13: INSUFFICIENT_DATA

Moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md) - load on demand (see References below).

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

Moved verbatim to [references/worked-examples.md](references/worked-examples.md) - load on demand (see References below).

### Worked example — Pre-token-generation Lambda error

Moved verbatim to [references/worked-examples.md](references/worked-examples.md) - load on demand (see References below).

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

Moved verbatim to [references/cognito-troubleshooting-commands.md](references/cognito-troubleshooting-commands.md) - load on demand (see References below).

## Remediation guidance

Moved verbatim to [references/error-handling.md](references/error-handling.md) - load on demand (see References below).

## Deep reference: Cognito authentication layer model

Moved verbatim to [references/cognito-auth-flow-reference.md](references/cognito-auth-flow-reference.md) - load on demand (see References below).

## Recent AWS features (2024-2026)

Moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md) - load on demand (see References below).

## References (load on demand)

- [references/advanced-patterns.md](references/advanced-patterns.md) - quick-start detail, mindset/philosophy/expert heuristics, Step 0 gotchas, extended branches (Steps 8-13), recent AWS features
- [references/worked-examples.md](references/worked-examples.md) - secondary worked examples (identity pool trust, pre-token Lambda)
- [references/error-handling.md](references/error-handling.md) - remediation guidance per layer
- [references/cognito-auth-flow-reference.md](references/cognito-auth-flow-reference.md) - auth-flow layer model, token lifecycle, Steps 3/5 detail
- [references/cognito-troubleshooting-commands.md](references/cognito-troubleshooting-commands.md) - pre-flight command listings + safety checks

## Domain

AWS CloudOps / Cognito Identity, Authentication and Authorization
Diagnostics, User Pool, Identity Pool, Federated Identities, Lambda
Triggers, and Social / SAML Provider Integration.

## AWS documentation

Moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md) - load on demand (see References below).

