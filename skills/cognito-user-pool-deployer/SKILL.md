---
name: cognito-user-pool-deployer
description: Provisions Amazon Cognito user pools with secure defaults — user pool attributes (standard and custom), password policy, MFA (SMS/TOTP), app clients (OAuth code+PKCE, client credentials), hosted UI customization, identity providers (SAML/OIDC/Social), Lambda triggers (pre-signup, post-confirmation, custom message, pre-token-generation), user pool groups, resource servers with custom scopes, domain (Cognito or custom), advanced security features (ASF ENFORCED), and hosted UI branding. Runs pre-checks (attribute schema, MFA SNS prerequisites, Lambda ARNs, custom domain ACM cert, IdP metadata, IAM permissions), emits create-user-pool and create-user-pool-client CLIs behind a CONFIRM gate, verifies via describe-user-pool. Emits READY_TO_DEPLOY | PREREQUISITES_MISSING. Use when creating user pools, configuring OAuth clients, federating SAML/OIDC, or enabling advanced security features.
license: Apache-2.0
compatibility: Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). No AWS CLI required for offline plan classification. Live-account operations use aws cognito-idp create-user-pool, create-user-pool-client, create-identity-provider, create-resource-server, create-group, create-user-pool-domain, update-user-pool, describe-user-pool (AWS CLI v2, SSO or key-based credentials).
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: 'true'
  phase: '1'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: Security
  task_type: deploy
  skill_class: capability
  lifecycle_status: active
  verdict_shape: READY_TO_DEPLOY | PREREQUISITES_MISSING
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  tags: cognito, security, identity, mfa, oauth, saml, oidc, deploy, user-pool, hosted-ui
  dependencies: aws-orchestrator
  keywords: Cognito, user pool, identity provider, IdP, MFA, TOTP, SMS MFA, password policy, app client, OAuth, code flow, PKCE, client credentials, SAML, OIDC, social login, hosted UI, branding, Lambda triggers, pre-signup, post-confirmation, custom message, pre-token-generation, resource server, custom scopes, user pool groups, custom domain, advanced security features, ASF, cognito-idp
  when_to_use: Creating a new Cognito user pool, configuring an OAuth app client, federating with SAML/OIDC/social identity providers, setting up hosted UI branding, wiring Lambda triggers (pre-signup, post- confirmation, custom message, pre-token-generation), enabling advanced security features (ASF ENFORCED), or registering a custom domain for the hosted UI.
  activation_triggers: create Cognito user pool, provision user pool, deploy Cognito, OAuth app client, code flow with PKCE, client credentials grant, SAML federation, OIDC identity provider, social login, hosted UI, Cognito branding, pre-signup trigger, post-confirmation trigger, custom message trigger, pre-token-generation trigger, resource server custom scopes, user pool groups, custom domain Cognito, advanced security features, cognito-idp create-user-pool
  invocation_schema: 'Input: either (a) a user pool deployment intent (create, update) with target pool name, attribute schema, password policy, MFA mode, app client OAuth config, identity providers, Lambda triggers, resource servers, groups, and domain; OR (b) a user pool id for live-account update or validation. Output: deterministic POOL/VERDICT/PRE_CHECKS/ STEPS/POST_VERIFY block per operation, where VERDICT is one of READY_TO_DEPLOY, PREREQUISITES_MISSING.'
---

# Cognito User Pool Deployer

## What this skill does

Provisions Amazon Cognito user pools with secure identity defaults —
correct attribute schema, password policy, MFA (TOTP preferred over SMS),
OAuth code flow with PKCE (never implicit), SRP-only auth flows,
`PreventUserExistenceErrors: ENABLED`, and Advanced Security Features
(ASF) in ENFORCED mode. Runs deterministic pre-checks before any
state-changing CLI (does the SMS-MFA SNS role exist? is the custom domain
ACM cert in us-east-1 and ISSUED? does the SAML IdP metadata resolve?
does the operator hold `cognito-idp:CreateUserPool`?), emits the exact
`create-user-pool` and `create-user-pool-client` CLIs behind a CONFIRM
gate, and verifies the pool via `describe-user-pool`. Every pool plan
surfaces the implicit-flow block, the ADMIN auth flow block, the deletion
protection default, and the token validity ceiling.

## Quick navigation

| Section | What it covers | When to read it |
|---|---|---|
| **Quick reference** | Verdict thresholds + pre-check priority order + pool config matrix | Before any operation |
| **Mindset** | Why defaults matter; Cognito silent-failure modes; overwrite traps | Understanding the deployment model |
| **Pre-flight** | Pool metadata gate — IdP metadata, ACM cert, SNS role, Lambda ARNs | Before executing any CLI |
| **Process** | Per-operation planning: create, update, add IdP, register domain | When choosing which operation |
| **Common patterns** | Production user pool / SAML federation / client credentials / custom domain boilerplate | Boilerplate lookup |
| **STRICT output contract** | Required POOL/VERDICT/PRE_CHECKS/STEPS/POST_VERIFY block | Formatting the response |
| **NEVER (top 5)** | Hard rules that prevent common insecure patterns | Review before deploy |
| **Expert heuristic** | When MFA mode is acceptable per use case | Choosing MFA strategy |

## Quick reference — verdict thresholds

| Verdict | Trigger condition | Action |
|---|---|---|
| `PREREQUISITES_MISSING` | Any pre-check failed (SNS role missing for SMS MFA, ACM cert wrong region/ISSUED pending, IdP metadata unresolvable, Lambda ARN invalid, IAM permission missing, Implicit OAuth flow requested, ADMIN auth flow requested, duplicate pool/client name, custom attribute deviates from `custom:` prefix, deletion protection inactive on update) | List failures, do NOT execute |
| `READY_TO_DEPLOY` | All pre-checks passed; awaiting CONFIRM gate | Emit exact CLI sequence with full pool config, wait for operator yes |

**Priority order for pre-checks (apply in this sequence, all must pass for
READY_TO_DEPLOY):**

1. **Pool name uniqueness** — `list-user-pools` returns no pool with the
   target name (for create) or matches exactly one (for update).
2. **Deletion protection** — for update operations, the existing pool has
   `DeletionProtection: ACTIVE`. Updating a pool with `INACTIVE` deletion
   protection blocks production-grade deploys.
3. **Attribute schema** — every standard attribute referenced in
   `RequiredAttributes` is in `Schema` (auto-added by Cognito but
   explicitly declared is safer). Custom attributes use `custom:` prefix
   and the type is consistent.
4. **Password policy** — minimum length >= 12, contains uppercase,
   lowercase, numbers, symbols. `TemporaryPasswordValidityDays` <= 7.
5. **MFA prerequisites** — if `MfaConfiguration: ON` with SMS:
   `sms_configuration.SnsCallerArn` resolves to an IAM role in the
   account; if TOTP only: no SNS role required.
6. **App client auth flows** — only `ALLOW_USER_SRP_AUTH` and
   `ALLOW_REFRESH_TOKEN_AUTH` allowed. `ALLOW_ADMIN_USER_PASSWORD_AUTH`
   and `ALLOW_USER_PASSWORD_AUTH` are blocked.
7. **OAuth flows** — only `code` grant allowed. `implicit` grant is
   blocked. `client-credentials` requires a resource server with scopes
   and `GenerateClientSecret: true`.
8. **PreventUserExistenceErrors** — set to `ENABLED` (default for new
   pools). `LEGACY` is blocked.
9. **Advanced Security Features** — `UserPoolAddOns.AdvancedSecurityMode`
   is `ENFORCED` (not `AUDIT` or `OFF`).
10. **Token validity** — `AccessTokenValidity` 5 min - 1 hour,
    `IdTokenValidity` 5 min - 1 hour, `RefreshTokenValidity` 1-3650 days.
11. **Identity provider metadata** — for SAML: metadata document or
    metadata URL resolves; for OIDC: issuer URL, authorize/auth/userinfo
    endpoints resolve and client credentials provided.
12. **Lambda triggers** — every ARN in `LambdaConfig` resolves via
    `lambda:get-function` and the pool has `lambda:InvokeFunction`
    permission via resource-based policy.
13. **Custom domain ACM cert** — if `CustomDomainConfig` is set, the ACM
    certificate ARN is in us-east-1 and status is `ISSUED`. The cert
    subject/alt names cover the domain.
14. **IAM permissions** — the operator principal holds
    `cognito-idp:CreateUserPool` (and `iam:PassRole` if SMS SNS role
    configured).

**Cognito limits (2026):**

- User pools per account (default): 1000 (soft limit).
- App clients per user pool: 1000.
- Identity providers per user pool: 100.
- Resource servers per user pool: 100.
- Custom attributes per pool: 25.
- User pool groups per pool: 1000.
- Hosted UI domain name length: 63 chars, alphanumeric + hyphen.
- RefreshTokenValidity max: 3650 days.

## Mindset

**One-line takeaway:** Cognito silently accepts insecure configurations.
A pool with `MfaConfiguration: OFF`, an app client with
`ALLOW_USER_PASSWORD_AUTH`, or an OAuth `implicit` grant will all deploy
successfully and operate — until a credential is leaked or an attacker
enumerates users. The skill enforces the secure-by-default stance by
blocking these patterns at the pre-check gate rather than at runtime.

Driven by three Cognito realities:

- **create-user-pool is all-or-nothing on the schema.** The
  `Schema` array can be set only at pool creation. Adding a required
  attribute to an existing pool requires migration to a new pool.
  Pre-flight attribute schema validation is non-negotiable — missing an
  attribute at create time means a multi-week user migration to fix.

- **MFA configuration is per-pool, but MFA factors are per-user.**
  `MfaConfiguration: ON` requires every user to set up MFA, but
  `ENABLED` (optional) lets users skip. SMS MFA requires an SNS caller
  role — if the role is missing, the pool will deploy and users will
  receive sign-in errors at the moment they try to set up SMS. The
  pre-flight gate catches this at deploy time.

- **App client settings silently downgrade security.** An app client
  with `GenerateClientSecret: false` (public client) is valid for
  mobile/SPA scenarios, but combined with `ALLOW_USER_PASSWORD_AUTH` it
  leaks credentials to the client. The skill blocks this combination
  at the pre-check gate rather than at runtime.

## Pre-flight: user pool metadata gate

Run before classification. Misclassifying these produces wrong plans.

Moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md) - load on demand (see References below).

**Malformed input:** if the pool spec is missing required fields
(`PoolName`, `Policies.PasswordPolicy`, or `MfaConfiguration`), emit
`VERDICT: PREREQUISITES_MISSING` with `REASON: Pool spec missing required
field — PoolName, PasswordPolicy, or MfaConfiguration. Cannot plan.` and
`REMEDIATION: Provide the full pool configuration per
https://docs.aws.amazon.com/cognito/latest/developerguide/cognito-user-pools-create-ing-cli.html.`

| Attribute | Effect on operation |
|---|---|
| Pool name already exists | Update operation. Must snapshot existing config first. Schema changes will be rejected. |
| SMS MFA without SNS caller role | Users will see "Invalid SMS role" at sign-up. PREREQUISITES_MISSING. |
| Custom attribute without `custom:` prefix | Cognito rejects the schema. PREREQUISITES_MISSING. |
| OAuth `implicit` grant requested | Token leakage via URL fragment. PREREQUISITES_MISSING — blocked at pre-check. |
| `ALLOW_ADMIN_USER_PASSWORD_AUTH` requested | Bypasses SRP, leaks admin creds. PREREQUISITES_MISSING — blocked at pre-check. |
| ACM cert in non-us-east-1 region | Custom domain will not validate. PREREQUISITES_MISSING. |
| Lambda trigger ARN not invocable | Trigger silently does not fire. PREREQUISITES_MISSING. |
| ASF mode `AUDIT` only | Adaptive protection logs but does not enforce. Flag in NOTES, allow if user-acknowledged. |

## Process — operation planning (apply in order)

### Step 0: Expert knowledge — non-obvious Cognito behaviors

Moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md) - load on demand (see References below).

### Step 1: Pre-check gate — PREREQUISITES_MISSING if any check fails

Run ALL of the following pre-checks. If ANY fails, the verdict is
PREREQUISITES_MISSING with the failed checks enumerated in PRE_CHECKS.
Do NOT execute.

**For ALL operations:**
1. Pool name is set, <= 128 chars, matches `[\w\s+=,.@-]+`.
2. Password policy minimum length >= 12, all character classes true,
   `TemporaryPasswordValidityDays` <= 7.
3. `MfaConfiguration` is one of `OFF`, `ON`, `OPTIONAL`.
4. `PreventUserExistenceErrors: ENABLED`.
5. `DeletionProtection: ACTIVE`.
6. `UserPoolAddOns.AdvancedSecurityMode: ENFORCED`.
7. IAM principal holds `cognito-idp:CreateUserPool`.

**For create-user-pool:**
8. Pool name does not collide with an existing pool (`list-user-pools`).
9. Schema: each custom attribute prefixed with `custom:`, type matches.
10. RequiredAttributes is a subset of Schema (or auto-added standard
    attributes).
11. `UsernameAttributes` is either `["email"]`, `["phone_number"]`, or
    `["email","phone_number"]`. Empty = username (alias) mode.
12. `AccountRecoverySetting`Mechanisms are valid (verified_email,
    verified_phone_number, etc.).

**For SMS MFA (MfaConfiguration ON with SMS in EnabledMfas):**
13. `SmsConfiguration.SnsCallerArn` resolves to an IAM role.
14. The role trusts `cognito-idp.amazonaws.com` and has
    `sns:Publish` permission.
15. ExternalId is set on the trust policy.

**For app client (create-user-pool-client):**
16. `ExplicitAuthFlows` contains ONLY `ALLOW_USER_SRP_AUTH` and
    `ALLOW_REFRESH_TOKEN_AUTH` (server-side clients may add
    `ALLOW_USER_PASSWORD_AUTH` with a documented justification).
17. `AllowedOAuthFlows` contains ONLY `code` (and optionally
    `client-credentials` if a resource server is configured).
    `implicit` is BLOCKED.
18. `GenerateClientSecret: true` for confidential clients.
    Machine clients (`client-credentials`) MUST have it true.
19. `AllowedOAuthScopes` only references scopes defined on a resource
    server in this pool (besides standard `openid`, `email`,
    `phone`, `profile`).
20. `CallbackURLs` and `LogoutURLs` are HTTPS (HTTP only for localhost
    during development).
21. `EnableTokenRevocation: true`.
22. `AccessTokenValidity` and `IdTokenValidity` <= 1 hour (in explicit
    `TokenValidityUnits`).
23. `RefreshTokenValidity` <= 3650 days (10 years).

**For SAML identity provider:**
24. `ProviderDetails.MetadataFile` or `MetadataURL` is provided and
    resolves.
25. For MetadataURL: HTTPS endpoint reachable, returns XML with
    `EntityDescriptor`.

**For OIDC identity provider:**
26. `ProviderDetails.OIDCIssuer` is HTTPS URL.
27. `authorize`, `token`, `userInfo` endpoints resolvable from
    `.well-known/openid-configuration`.
28. `ClientId` and `ClientSecret` set.

**For Lambda triggers (LambdaConfig):**
29. Every ARN resolves via `lambda:get-function`.
30. The user pool service principal has `lambda:InvokeFunction` on each
    function's resource-based policy.

**For custom domain (CustomDomainConfig):**
31. ACM cert ARN is in us-east-1.
32. `describe-certificate` returns status `ISSUED`.
33. Cert subject/alt names cover the custom domain.

### Step 2: READY_TO_DEPLOY — emit deployment plan

If all pre-checks pass, emit `VERDICT: READY_TO_DEPLOY` with the exact
CLI sequence and the CONFIRM gate. The plan includes:

- The exact `aws cognito-idp create-user-pool` CLI with the full config
  (Schema, Policies, MfaConfiguration, UserPoolAddOns, LambdaConfig,
  AccountRecoverySetting, DeletionProtection).
- The follow-up `create-user-pool-client` CLI for each app client.
- The follow-up `create-identity-provider` CLI for each IdP.
- The follow-up `create-resource-server` CLI for each resource server.
- The follow-up `create-group` CLI for each group.
- The follow-up `create-user-pool-domain` (Cognito or custom) CLI.
- The CONFIRM gate prompt.

### Step 3: Execute behind CONFIRM gate

- **MANDATORY CONFIRMATION GATE.** Before any state-changing CLI
  (`create-user-pool`, `update-user-pool`, `delete-user-pool`), emit:
  `CONFIRM: About to <operation> user pool <name> in account <account>
  region <region>. This will <consequence>. Proceed? (yes/no)`. Do NOT
  execute until the operator confirms.
- Snapshot the current pool config before modification:
  `aws cognito-idp describe-user-pool --user-pool-id <id> --output json
  > /tmp/<pool-name>-backup-$(date +%s).json`.
- Execute the CLI with the full pool config.

### Step 4: Post-verification

After the operation finishes, run post-verification:

1. `describe-user-pool --user-pool-id <id>` returns the expected pool
   config (Schema, Policies, MfaConfiguration, UserPoolAddOns).
2. `list-user-pool-clients --user-pool-id <id>` returns the expected
   clients with correct ExplicitAuthFlows.
3. For SMS MFA: `list-identity-providers` (no-op verification — IAM role
   is exercised only at user sign-up time, but the role exists).
4. For Lambda triggers: invoke the trigger manually with a synthetic
   event to confirm the resource-based policy allows the pool to call.
5. For custom domain: `describe-user-pool-domain --domain <domain>`
   returns status `CREATING`, then `ACTIVE` (verify DNS).

## Common pool patterns (boilerplate)

Moved verbatim to [references/worked-examples.md](references/worked-examples.md) - load on demand (see References below).

## STRICT output contract

### Required output structure

Every response MUST begin with this block — no preamble, no conversational
opening:

```text
POOL: <pool-name>
VERDICT: READY_TO_DEPLOY | PREREQUISITES_MISSING
TARGET: <pool-name> (pool-id: <id> for updates)
PRE_CHECKS:
  - [PASS] <check description>
  - [FAIL] <check description> — <reason>
STEPS:
  1. CONFIRM: About to <operation> pool <name> in account <account> region <region>. This will <consequence>. Proceed? (yes/no)
  2. <exact CLI command — no placeholders>
POST_VERIFY:
  - [PASS] <verification description>
  - [FAIL] <verification description> — <reason>
ATTRIBUTES: <count> standard, <count> custom
MFA: OFF | TOTP-only | SMS-only | TOTP+SMS (config: ON|OPTIONAL)
OAUTH_FLOWS: code | client-credentials | (blocked: implicit)
IDPS: <count> SAML, <count> OIDC, <count> social
ASF: ENFORCED | AUDIT | OFF
NOTES: <security posture, MFA strategy, attribute schema caveats>
```

### FORBIDDEN output patterns

- NEVER start with "Let me analyze…" or "I'll create…" — the VERDICT
  block is the FIRST line, always. No conversational preamble.
- NEVER use lowercase verdict values — emit `READY_TO_DEPLOY` or
  `PREREQUISITES_MISSING` (not `ready`, `prerequisites`).
- NEVER omit PRE_CHECKS — every pre-check run must appear with `[PASS]`
  or `[FAIL]` and a specific reason for each failure. An empty
  PRE_CHECKS block is non-compliant.
- NEVER emit a plan with placeholder values (e.g., `<pool-id>`,
  `<account-id>`) in a READY_TO_DEPLOY plan — every field must be
  populated with actual values from the input.
- NEVER omit the CONFIRM gate as the first STEPS entry for any
  state-changing operation.
- NEVER claim success without verifying that the pool was created
  (via `describe-user-pool`) — a partial CLI sequence with missing
  required subcommands is non-compliant.
- NEVER put-update a pool without snapshotting the existing config first
  — updates to `LambdaConfig` and `MfaConfiguration` overwrite silently.
- NEVER silently allow `implicit` OAuth flow — block it explicitly with
  a [FAIL] pre-check row naming the security risk.

### Perfect example output

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
  1. CONFIRM: About to create-user-pool prod-users in account 111111111111 region us-east-1. This will CREATE a new user pool with TOTP MFA, 4 attributes, and ENFORCED ASF. Proceed? (yes/no)
  2. aws cognito-idp create-user-pool --pool-name prod-users --policies '{...}' --mfa-configuration ON --enabled-mfas '["TOTP"]' --username-attributes '["email"]' --schema '[...]' --user-pool-add-ons 'AdvancedSecurityMode=ENFORCED' --deletion-protection ACTIVE --prevent-user-existence-errors ENABLED
  3. aws cognito-idp create-user-pool-client --user-pool-id <returned-id> --client-name prod-web-spa --generate-client-secret --explicit-auth-flows ALLOW_USER_SRP_AUTH ALLOW_REFRESH_TOKEN_AUTH --allowed-o-auth-flows code --allowed-o-auth-scopes openid email profile --callback-urls '["https://app.example.com/callback"]' --logout-urls '["https://app.example.com/logout"]' --access-token-validity 1 --id-token-validity 1 --token-validity-units '{"AccessToken":"hours","IdToken":"hours"}' --refresh-token-validity 30 --enable-token-revocation --prevent-user-existence-errors ENABLED
POST_VERIFY:
  - (pending execution)
  - describe-user-pool returns the pool with MfaConfiguration=ON, AdvancedSecurityMode=ENFORCED
  - list-user-pool-clients returns prod-web-spa with ExplicitAuthFlows=[ALLOW_USER_SRP_AUTH, ALLOW_REFRESH_TOKEN_AUTH]
ATTRIBUTES: 3 standard (email, given_name, family_name), 1 custom (custom:tenantId)
MFA: TOTP-only (config: ON)
OAUTH_FLOWS: code
IDPS: 0 SAML, 0 OIDC, 0 social
ASF: ENFORCED
NOTES:
  - TOTP-only MFA avoids SNS SMS per-message cost — users enroll via authenticator app (Google Authenticator, Authy, 1Password).
  - RefreshTokenValidity 30 days balances UX and security; reduce to 1 day for high-trust environments.
  - Custom attribute custom:tenantId is immutable — set once at signup via pre-signup Lambda.
  - Add the identity pool later if you need AWS credential vending to authenticated users (out of scope here).
```

## NEVER (top 5)

These are the highest-impact, most-frequent failure modes in Cognito
deployments. Violating any one of these is a security regression.

1. **NEVER enable OAuth `implicit` flow.** Tokens are returned via the
   URL fragment — leaks via browser history, Referer headers, and
   proxy logs. Always use `code` grant with PKCE for SPA and mobile
   clients. Block at pre-check; never silently rewrite.

2. **NEVER enable `ALLOW_ADMIN_USER_PASSWORD_AUTH` on a public client.**
   It bypasses SRP, exposes admin credentials to the client, and is
   the #1 path to credential compromise. For confidential server-side
   clients only, and only with documented justification. Block at
   pre-check.

3. **NEVER create a user pool without `DeletionProtection: ACTIVE`.**
   Accidental pool deletion destroys user accounts with no recovery —
   Cognito has no recycle bin. Active protection requires an explicit
   `--deletion-protection INACTIVE` step before delete.

4. **NEVER deploy SMS MFA without verifying the SNS caller role.**
   The pool will deploy cleanly but every SMS-OTP sign-up will fail
   with "Invalid SMS role" at the moment a user tries to enroll. Verify
   the role exists, trusts `cognito-idp.amazonaws.com`, has
   `sns:Publish`, and uses `ExternalId` for cross-account trust.

5. **NEVER put a custom attribute in `RequiredAttributes` without
   declaring it in `Schema`.** Cognito silently accepts but the
   attribute is never written — signups fail at the moment of attribute
   collection. Always declare in both arrays, prefixed with `custom:`.

## Expert heuristic: choosing MFA strategy

The right MFA strategy is a function of user population, network, and
cost tolerance — not a one-size-fits-all. The heuristic below resolves
the trade-off deterministically.

```
User population / environment
   ├─ B2C consumer app (mobile/web)?
   │    ├─ TOTP only (Authenticator app)
   │    │    Users install Google Authenticator once. No per-message
   │    │    cost. Works offline. Best UX if app supports enrollment QR.
   │    └─ SMS as backup only (OPTIONAL + both factors enabled)
   │         SMS incurs $0.00645/msg in the US, more internationally.
   │         Use only when TOTP is impossible (low-tech user base).
   │
   ├─ B2B / workforce?
   │    └─ TOTP only. Strict ON policy. No SMS — corporate devices
   │         support authenticators and SMS is exposed to SIM swap.
   │
   ├─ Regulated (PCI/HIPAA/Government)?
   │    └─ TOTP ON + ASF ENFORCED. SMS not accepted by most auditors
   │         as a second factor — SIM swap is a recognized attack.
   │
   └─ Development / staging?
        └─ MFA OFF acceptable if ASF ENFORCED for adaptive defense.
             Production must still enforce TOTP ON. NEVER disable ASF.
```

**Decision rules:**
- Default to TOTP-only. Add SMS only if (a) the user population cannot
  install authenticators, OR (b) a documented regulation requires it.
- Always pair MFA with ASF ENFORCED. MFA alone does not stop credential
  stuffing — ASF detects the pattern.
- SMS requires an SNS caller role with cross-account ExternalId. The
  pre-check gate verifies this.
- TOTP enrollment requires a per-user `SoftwareTokenMfaSettings` write
  via `cognito-idp:associate-software-token` — outside the deploy scope
  but flag in NOTES for the application team.

ALWAYS emit `AdvancedSecurityMode: ENFORCED` for production pools. AUDIT
mode is acceptable only in staging for evaluating ASF false-positive
rates before promoting to ENFORCED.

## Recent AWS features (2024-2026)

Moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md) - load on demand (see References below).

## AWS documentation

- **Amazon Cognito User Pools Developer Guide** — https://docs.aws.amazon.com/cognito/latest/developerguide/cognito-user-identity-pools.html
- **User pool attributes** — https://docs.aws.amazon.com/cognito/latest/developerguide/user-pool-settings-attributes.html
- **MFA in user pools** — https://docs.aws.amazon.com/cognito/latest/developerguide/user-pool-settings-mfa.html
- **App client OAuth 2.0 flows** — https://docs.aws.amazon.com/cognito/latest/developerguide/cognito-user-pools-app-idp-settings.html
- **SAML federation** — https://docs.aws.amazon.com/cognito/latest/developerguide/cognito-user-pools-saml-idp.html
- **OIDC federation** — https://docs.aws.amazon.com/cognito/latest/developerguide/cognito-user-pools-oidc-idp.html
- **Lambda triggers** — https://docs.aws.amazon.com/cognito/latest/developerguide/cognito-user-identity-pools-working-with-aws-lambda-triggers.html
- **Resource servers and custom scopes** — https://docs.aws.amazon.com/cognito/latest/developerguide/cognito-user-pools-define-resource-servers.html
- **Advanced Security Features** — https://docs.aws.amazon.com/cognito/latest/developerguide/cognito-user-pool-settings-advanced-security.html
- **Managed Login Branding** — https://docs.aws.amazon.com/cognito/latest/developerguide/managed-login-branding.html

## References (load on demand)

- [references/advanced-patterns.md](references/advanced-patterns.md) — Step-0 expert Cognito behaviors and 2024-2026 feature changes moved from SKILL.md
- [references/worked-examples.md](references/worked-examples.md) — common pool / client / IdP / domain / trigger / group CLI boilerplate moved from SKILL.md
- [references/diagnostic-commands.md](references/diagnostic-commands.md) — live-account pre-flight command listing moved from SKILL.md
- [references/pool-config-and-security-defaults.md](references/pool-config-and-security-defaults.md) — pool archetypes, app client procedure, token validity, verification commands
- [references/identity-providers-and-triggers.md](references/identity-providers-and-triggers.md) — SAML/OIDC/social IdP, Lambda trigger, and domain procedures

## Domain

AWS CloudOps / Identity & Access Management — Cognito User Pool Provisioning.
