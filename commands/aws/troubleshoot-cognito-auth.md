---
description: Diagnoses Amazon Cognito authentication failures through a twelve-category diagnostic tree (app client, auth flow, hosted UI redirect, token refresh, Lambda triggers, identity pool roles, social provider, SAML, MFA, password policy, custom attributes, domain, TLS) — emits ROOT_CAUSE_IDENTIFIED with the specific failure layer or INSUFFICIENT_DATA.
nl_triggers:
  - "Cognito authentication failed"
  - "Cognito NotAuthorizedException"
  - "Cognito UserLambdaValidationException"
  - "Cognito redirect_mismatch"
  - "Cognito hosted UI callback"
  - "Cognito token refresh failed"
  - "Cognito InvalidGrantException"
  - "Cognito pre-token-generation Lambda"
  - "Cognito identity pool role"
  - "Cognito unauthenticated role"
  - "Cognito social provider Google"
  - "Cognito Facebook login"
  - "Cognito SignInWithApple"
  - "Cognito SAML provider"
  - "Cognito SAML certificate"
  - "Cognito MFA setup failed"
  - "Cognito password policy"
  - "Cognito custom attributes"
  - "Cognito domain prefix"
  - "Cognito TLS certificate"
  - "troubleshoot Cognito authentication"
  - "users cannot log in Cognito"
routes_to: cognito-auth-troubleshooter
---

# /aws:troubleshoot-cognito-auth

Activate the `cognito-auth-troubleshooter` skill and diagnose an Amazon
Cognito authentication failure through the twelve-category diagnostic
tree.

## What it does

Reads a symptom description (error message, observed behaviour, client
context) plus the User Pool / Identity Pool configuration, then walks
the symptom-driven diagnostic tree to a root cause with positive
evidence:

1. **Pre-flight** — User Pool config (`describe-user-pool`), App Client
   config (`describe-user-pool-client`), Identity Pool config
   (`describe-identity-pool`, `get-identity-pool-roles`), trigger Lambda
   logs (`filter-log-events`), AWS Health (regional incidents).
   Short-circuits on stale MFA settings, missing domain, wrong
   `ClientSecret` presence, or AWS-side Cognito service events.
2. **Symptom entry** — map the error to one of: app client secret
   mismatch, auth flow error, hosted UI redirect mismatch, token refresh
   failure, Lambda trigger error, identity pool role / trust failure,
   social provider misconfiguration, SAML provider / certificate
   mismatch, MFA setup / bypass, password policy violation, custom
   attribute write failure, domain prefix conflict, TLS certificate
   issue.
3. **Layer-specific probes** —
   - App client: `ClientSecret` presence (PUBLIC vs CONFIDENTIAL),
     `ExplicitAuthFlows` allow list, `AllowedOAuthFlows`.
   - Hosted UI: `CallbackURLs` exact match against `redirect_uri`
     (scheme, host, port, path, trailing slash, case).
   - Token refresh: `RefreshTokenValidity` + `TokenValidityUnits`,
     CloudTrail for `RevokeToken` / `GlobalSignOut`.
   - Lambda triggers: CloudWatch Logs for the trigger Lambda, response
     shape and size validation.
   - Identity pool: `get-identity-pool-roles` + IAM role trust policy
     (Principal must be `cognito-identity.amazonaws.com`, `aud` must
     match pool ID, `amr` must contain `unauth` for unauthenticated).
   - Social provider: provider redirect URI consistency, credentials,
     attribute mapping, `SupportedIdentityProviders`.
   - SAML: metadata freshness, certificate match, IdP Entity ID /
     Audience.
   - MFA: pool-level vs per-user setting, TOTP enrolment sequence, SMS
     delivery via SNS.
   - Password: policy fields (`MinimumLength`, `Require*` flags).
   - Custom attributes: `Mutable` flag, `DeveloperOnlyAttribute`.
   - Domain: `describe-user-pool-domain`, ACM certificate status.
4. **Verdict** — ROOT_CAUSE_IDENTIFIED (with failing probe that matches
   the symptom) or INSUFFICIENT_DATA (a probe requires operator input
   or AWS-side incident is suspected).

Emits a deterministic diagnostic block per target:

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
```

## When to invoke

Paste a symptom description and ask any of:

- "Cognito redirect_mismatch on hosted UI"
- "Cognito NotAuthorizedException invalid_client"
- "Cognito token refresh returns InvalidGrantException"
- "Cognito UserLambdaValidationException on sign-in"
- "Cognito identity pool unauthenticated access denied"
- "Cognito SAML login returns SAMLResponseDoesNotMatch"
- "Cognito Google login shows blank page"
- "Cognito MFA code rejected"

A bare pool ID + any error verb ("users cannot log in", "auth failing",
"token expired") also routes here via the orchestrator.

## Inputs

- Symptom description: error string, observed behaviour, which users
  are affected (all vs subset), when it started.
- Pool / Client configuration: UserPoolId, AppClientId, auth flow used,
  ClientSecret presence, CallbackURLs, ExplicitAuthFlows, LambdaConfig,
  MfaConfiguration.
- For live-account diagnosis: IdentityPoolId (for identity pool issues),
  provider name (for social / SAML issues), trigger Lambda name and
  CloudWatch logs. The skill uses `describe-user-pool`,
  `describe-user-pool-client`, `describe-identity-provider`,
  `describe-identity-pool`, `get-identity-pool-roles`, `get-role`,
  `filter-log-events`, `cloudtrail lookup-events`,
  `describe-user-pool-domain`, `acm describe-certificate`.

## Outputs

- One diagnostic block per target pool / client / provider.
- Layer-specific LAYER value from the enumerated set.
- Evidence section with the failing probe AND passing probes (layers
  ruled out) — never a verdict without positive evidence.
- Specific remediation: update app client, update trust policy, update
  provider metadata, fix Lambda code, update MFA config, update password
  policy, add callback URL, or AWS Support escalation.

## Related

- `/aws:pipeline` to enter the full CloudOps pipeline (this skill is
  the Phase 2 Troubleshoot specialist for Cognito authentication
  failures).
- `/aws:troubleshoot-iam-permission` for deeper diagnosis when the
  identity pool role is denied by an SCP, permissions boundary, or
  session policy.
- `/aws:troubleshoot-lambda-invocation` for deeper diagnosis when a
  Cognito trigger Lambda fails (timeout, OOM, AccessDenied on
  downstream calls).
