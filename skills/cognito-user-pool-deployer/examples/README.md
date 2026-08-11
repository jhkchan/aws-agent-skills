# End-to-end usage scenario: cognito-user-pool-deployer

A walkthrough showing the skill creating a standard production user
pool with TOTP MFA, then extending it with a SAML federation provider,
and finally blocking an attempt to enable OAuth implicit flow. Each
path includes pre-checks, CONFIRM gate, and post-verification.

## Input (user prompt)

> Create a production user pool "prod-users" in us-east-1 with email
> login, TOTP MFA ON, ENFORCED ASF, and a `prod-web-spa` app client
> using OAuth code flow with PKCE. Then federate it with Okta SAML
> for our workforce users. Finally, the legacy SPA team wants implicit
> flow — block that.

```json
{
  "Operation": "create",
  "Pool name": "prod-users",
  "Region": "us-east-1",
  "Account": "111111111111",
  "UsernameAttributes": ["email"],
  "Schema": [
    {"Name": "email", "Type": "String", "Required": true, "Mutable": false},
    {"Name": "given_name", "Type": "String", "Required": true},
    {"Name": "family_name", "Type": "String", "Required": true},
    {"Name": "custom:tenantId", "Type": "String", "Mutable": false}
  ],
  "MfaConfiguration": "ON",
  "EnabledMfas": ["TOTP"],
  "AdvancedSecurityMode": "ENFORCED",
  "DeletionProtection": "ACTIVE",
  "AppClient": {
    "Name": "prod-web-spa",
    "ExplicitAuthFlows": ["ALLOW_USER_SRP_AUTH", "ALLOW_REFRESH_TOKEN_AUTH"],
    "AllowedOAuthFlows": ["code"],
    "AllowedOAuthScopes": ["openid", "email", "profile"],
    "CallbackURLs": ["https://app.example.com/callback"]
  }
}
```

## Skill output — create standard user pool

```text
POOL: prod-users
VERDICT: READY_TO_DEPLOY
TARGET: prod-users
PRE_CHECKS:
  - [PASS] Pool name unique (no collision in list-user-pools)
  - [PASS] Password policy: 16 chars, all classes, 1-day temp
  - [PASS] MFA: TOTP-only, no SMS role required
  - [PASS] Username attributes: ["email"]
  - [PASS] Custom attributes prefixed custom: (custom:tenantId)
  - [PASS] DeletionProtection: ACTIVE
  - [PASS] PreventUserExistenceErrors: ENABLED
  - [PASS] AdvancedSecurityMode: ENFORCED
  - [PASS] Account recovery: verified_email (priority 1)
  - [PASS] IAM principal holds cognito-idp:CreateUserPool
STEPS:
  1. CONFIRM: About to create-user-pool prod-users in account
     111111111111 region us-east-1. This will CREATE a new user pool
     with TOTP MFA, 4 attributes, and ENFORCED ASF. Proceed? (yes/no)
  2. aws cognito-idp create-user-pool --pool-name prod-users
     --policies '{...}' --mfa-configuration ON --enabled-mfas '["TOTP"]'
     --schema '[...]' --user-pool-add-ons 'AdvancedSecurityMode=ENFORCED'
     --deletion-protection ACTIVE --prevent-user-existence-errors ENABLED
  3. aws cognito-idp create-user-pool-client --user-pool-id <returned-id>
     --client-name prod-web-spa --generate-client-secret
     --explicit-auth-flows ALLOW_USER_SRP_AUTH ALLOW_REFRESH_TOKEN_AUTH
     --allowed-o-auth-flows code --allowed-o-auth-scopes openid email profile
     --callback-urls '["https://app.example.com/callback"]'
POST_VERIFY:
  - (pending execution)
  - describe-user-pool returns MfaConfiguration=ON, AdvancedSecurityMode=ENFORCED
  - list-user-pool-clients returns prod-web-spa with correct auth flows
ATTRIBUTES: 3 standard, 1 custom (custom:tenantId)
MFA: TOTP-only (config: ON)
OAUTH_FLOWS: code
IDPS: 0 SAML, 0 OIDC, 0 social
ASF: ENFORCED
NOTES:
  - TOTP-only MFA avoids SNS SMS per-message cost. Users enroll via
    authenticator app (Google Authenticator, Authy, 1Password).
  - RefreshTokenValidity 30 days balances UX and security; reduce to
    1 day for high-trust environments.
  - Custom attribute custom:tenantId is immutable — set once at signup
    via pre-signup Lambda trigger.
```

## Skill output — SAML federation add-on

```text
POOL: prod-users
VERDICT: READY_TO_DEPLOY
TARGET: prod-users (pool-id: us-east-1_abc123)
PRE_CHECKS:
  - [PASS] SAML metadata URL resolves (200 OK, EntityDescriptor root)
  - [PASS] X509 signing certificate present in metadata
  - [PASS] Attribute mapping: 2 claims (email, given_name)
  - [PASS] Pool exists and is in ACTIVE state
  - [PASS] Provider name CorpOkta not already registered
STEPS:
  1. CONFIRM: About to create-identity-provider CorpOkta (SAML) on pool
     prod-users. This will enable workforce login via Okta. Proceed? (yes/no)
  2. aws cognito-idp create-identity-provider --user-pool-id us-east-1_abc123
     --provider-name CorpOkta --provider-type SAML
     --provider-details '{"MetadataURL":"https://corp.okta.com/..."}'
     --attribute-mapping '{"email":"...emailaddress","given_name":"...givenname"}'
POST_VERIFY:
  - (pending execution)
  - list-identity-providers returns CorpOkta (SAML)
ATTRIBUTES: 3 standard, 1 custom
MFA: TOTP-only (config: ON)
OAUTH_FLOWS: code
IDPS: 1 SAML, 0 OIDC, 0 social
ASF: ENFORCED
NOTES:
  - Configure the Okta SAML app ACS URL to
    https://prod-users.auth.us-east-1.amazoncognito.com/saml2/idpresponse.
  - IdP-initiated SSO requires the Okta SAML app to send the application
    relay state. Configure the relay state in Okta to the hosted UI URL.
  - IdP-initiated users have no password in Cognito — they always
    re-authenticate via SAML.
```

## Skill output — implicit flow blocked

```text
POOL: prod-users
VERDICT: PREREQUISITES_MISSING
TARGET: prod-users (pool-id: us-east-1_abc123)
PRE_CHECKS:
  - [PASS] Pool name not in collision (existing pool)
  - [PASS] Password policy: 16 chars, all classes
  - [PASS] DeletionProtection: ACTIVE
  - [PASS] PreventUserExistenceErrors: ENABLED
  - [PASS] AdvancedSecurityMode: ENFORCED
  - [FAIL] App client legacy-spa requests AllowedOAuthFlows=[code,implicit].
    OAuth implicit grant returns access tokens via the URL fragment —
    leaked via browser history, Referer headers, and proxy logs. The
    skill blocks implicit flow at the pre-check gate. Use code flow
    with PKCE (proof-key-for-code-exchange) for SPA clients; tokens
    are exchanged server-side via the client secret or PKCE verifier.
STEPS: (none — pre-checks failed; remove implicit from AllowedOAuthFlows)
POST_VERIFY: (none)
ATTRIBUTES: 1 standard (email)
MFA: TOTP-only (config: ON)
OAUTH_FLOWS: blocked (implicit detected; use code+PKCE)
IDPS: 0 SAML, 0 OIDC, 0 social
ASF: ENFORCED
NOTES:
  - Root cause: implicit grant in AllowedOAuthFlows. Cognito silently
    accepts this configuration and tokens would leak at runtime.
  - Remediation: set AllowedOAuthFlows to ["code"] and add a PKCE
    verifier in the SPA's OAuth library (AppAuth, MSALErrorCode.OAuth
    flows). For confidential clients (with GenerateClientSecret: true),
    code flow is the only secure grant.
  - Re-issue the create-user-pool-client with:
    --allowed-o-auth-flows code
    --allowed-o-auth-scopes openid email
    --callback-urls '["https://app.example.com/callback"]'
```

## What the skill caught that a generic assistant misses

1. **Pre-check gate before any CLI executes.** A generic assistant emits
   `create-user-pool` directly. The skill runs 10+ deterministic
   pre-checks and confirms the password policy, MFA prerequisites,
   attribute schema, deletion protection, ASF mode, and IAM permissions.

2. **Implicit-flow block.** A generic assistant includes implicit in
   `AllowedOAuthFlows` for "SPA convenience." The skill blocks it at
   the pre-check gate — token leakage is silent and exploitable.

3. **ADMIN auth flow block.** A generic assistant includes
   `ALLOW_ADMIN_USER_PASSWORD_AUTH` for admin tooling. The skill blocks
   it — admin auth bypasses SRP and is the #1 path to credential
   compromise.

4. **SMS MFA SNS role verification.** A generic assistant configures
   SMS MFA and walks away. The skill verifies the SNS caller role
   exists, trusts `cognito-idp.amazonaws.com`, and has `sns:Publish` —
   otherwise every SMS-OTP signup fails at runtime.

5. **Schema immutability awareness.** A generic assistant suggests
   "add custom attributes later." The skill knows Schema is immutable
   after creation and over-specifies attributes up front.

6. **Lambda trigger permission wiring.** A generic assistant sets
   `LambdaConfig` and assumes triggers will fire. The skill verifies
   the pool principal has `lambda:InvokeFunction` on each function's
   resource-based policy.

7. **ACM cert region for custom domain.** A generic assistant accepts
   any ACM cert ARN. The skill requires us-east-1 — custom domain
   validation silently fails otherwise.

8. **CONFIRM gate.** A generic assistant auto-executes. The skill emits
   `CONFIRM:` and waits — `create-user-pool` cannot be undone without
   a 30-day deletion window.

## Slash-command invocation

```
/aws:deploy-cognito-user-pool
```

Or via the orchestrator:

```
/aws:pipeline
You: "create a Cognito user pool with TOTP MFA"
```

The orchestrator emits
`[Phase: Deploy | Skills routed: cognito-user-pool-deployer]` and hands
off to this skill for the VERDICT.

## CLI routing

```bash
node cli/bin/cli.js route "create a cognito user pool"
# [Phase: Deploy | Skills routed: cognito-user-pool-deployer]
```

## Live-account follow-up (optional, requires AWS CLI)

After the pool is created:

```bash
# Verify the pool exists and has the expected config
aws cognito-idp describe-user-pool --user-pool-id us-east-1_abc123 \
  --profile default \
  --query 'UserPool.[PoolName,MfaConfiguration,DeletionProtection]'

# Verify app client auth flows
aws cognito-idp list-user-pool-clients --user-pool-id us-east-1_abc123 \
  --profile default \
  --query 'UserPoolClients[].[ClientName,ExplicitAuthFlows,AllowedOAuthFlows]'

# Verify ASF mode
aws cognito-idp describe-user-pool --user-pool-id us-east-1_abc123 \
  --profile default \
  --query 'UserPool.UserPoolAddOns.AdvancedSecurityMode'
```
