---
name: cognito-identity-pool-deployer
description: 'Provisions Amazon Cognito Identity Pools (federated identities) with production defaults: identity pool creation, identity providers (Cognito User Pool, Amazon, Google, Facebook, Apple, SAML, OIDC), authenticated vs unauthenticated roles, role mapping (rules-based vs token-based), custom IAM role assumption per provider, principal tag attribute mapping, SAML provider trust policy, identity pool authflow (GetId + GetCredentialsForIdentity), access control via groups, JWT claim extraction, and cross-account role assumption. Emits a READY_TO_DEPLOY checklist with verification commands. Use when creating a Cognito Identity Pool, configuring federated identity providers, setting up role mapping for per-provider IAM roles, enabling guest (unauthenticated) access, or mapping JWT claims to IAM roles. Triggers: create cognito identity pool, federated identity, cognito role mapping, identity pool provider, unauthenticated role, get credentials for identity, principal tags, SAML federation cognito.'
license: Apache-2.0
compatibility: 'Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). For live deployment: AWS CLI v2 with cognito-identity and iam access. Works with Terraform aws_cognito_identity_pool, aws_cognito_identity_pool_provider_config, and aws_iam_role resources and CloudFormation AWS::Cognito::IdentityPool templates.'
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
  tags: aws, cognito, identity-pool, cloudops, deploy, security, federated-identity, role-mapping, iam, authentication
  dependencies: aws-orchestrator
  keywords: aws, cognito, identity pool, federated identity, role mapping, unauthenticated role, authenticated role, jwt claims, principal tags, saml federation, cloudops, deploy, provisioning, security
  when_to_use: Invoke when the user wants to create a Cognito Identity Pool for federated identity — configuring identity providers (Cognito User Pool, social providers, SAML, OIDC), authenticated/unauthenticated IAM roles, rules-based or token-based role mapping, principal tag attribute mapping, or cross-account role assumption. Do NOT invoke for Cognito User Pools (use user-pool skills), IAM Identity Center (use identity-center skills), or STS federation directly.
---

# Cognito Identity Pool Deployer

An AWS CloudOps agent skill that provisions Amazon Cognito Identity
Pools (federated identities) with correct defaults. The skill walks
the operator through identity pool creation, identity provider
configuration, authenticated vs unauthenticated roles, role mapping
(rules-based vs token-based), principal tag mapping, the authflow
(GetId + GetCredentialsForIdentity), and JWT claim extraction,
captures provider and role mapping decisions, explains why each
default matters, and emits a READY_TO_DEPLOY checklist with copy-
pasteable verification commands.

## Activation keywords

create Cognito identity pool, federated identity, Cognito role
mapping, identity pool provider, unauthenticated role, get
credentials for identity, principal tags, SAML federation Cognito.

## STRICT output contract

When this skill is invoked with a Cognito Identity Pool provisioning
request (create an identity pool, configure providers, set up role
mapping, enable guest access, map JWT claims to roles, or a partial
configuration), the agent MUST respond with the READY_TO_DEPLOY
checklist defined in the "Output format" section using the literal
all-caps labels `COGNITO_IDENTITY_POOL:`, `VERDICT:`, `CHECKLIST:`,
and `VERIFICATION_COMMANDS:`. Do NOT preface the checklist with prose,
headings, or disclaimers — emit the block as the first lines of the
response. This contract is what assertion-based evals and downstream
provisioning pipelines rely on; deviating from the literal labels
breaks automation silently.

If any prerequisite is missing, the verdict is
`PREREQUISITES_MISSING` with a specific gap citation in the checklist
(marked `[x]`), and `READY_TO_DEPLOY` MUST NOT also appear.

## Quick navigation

| Section | When to read |
|---|---|
| Prerequisites | Always — verify before provisioning |
| Step 1 — Identity pool vs user pool distinction | Core concept |
| Step 2 — Identity providers configuration | Provider setup |
| Step 3 — Authenticated and unauthenticated roles | IAM role design |
| Step 4 — Role mapping (rules-based vs token-based) | Per-provider IAM |
| Step 5 — Principal tag attribute mapping | ABAC |
| Step 6 — SAML provider trust policy | SAML federation |
| Step 7 — Authflow: GetId + GetCredentialsForIdentity | Credential flow |
| Step 8 — Access control via groups and JWT claims | Group-based access |
| Step 9 — Cross-account role assumption | Multi-account federation |
| Step 10 — Recent features | Latest |
| NEVER do these things | Review before signing off |
| Output format | The literal checklist template |
| references/role-mapping-and-jwt.md | Role mapping detail |
| references/providers-and-trust.md | Provider + trust detail |

## Mindset

**One-line takeaway:** A Cognito Identity Pool GRANTS AWS CREDENTIALS
to federated users — it does NOT authenticate them. Authentication
happens at the identity provider (User Pool, Google, SAML, etc.).
The identity pool receives the provider's token and exchanges it for
temporary AWS credentials via STS. Role mapping rules evaluate JWT
claims to assign the correct IAM role per user.

Three misconceptions dominate Identity Pool misdesign at provisioning
time:

- **"Identity Pools authenticate users."** They do NOT. Identity Pools
  federate identities — they exchange external provider tokens for
  AWS credentials. The actual authentication is done by the identity
  provider (Cognito User Pool, Google, Facebook, Apple, SAML IdP,
  OIDC provider). The identity pool trusts the provider's assertion
  and grants credentials. Confusing the two leads to trying to
  configure passwords/MFA at the identity pool level, which is wrong.

- **"The authenticated role is enough for all users."** It is NOT for
  apps with varying access levels. The default authenticated role
  gives ALL authenticated users the same IAM permissions. For apps
  where different users need different AWS access (e.g., admins vs
  readers), you need rules-based role mapping — rules that evaluate
  JWT claims (like group membership) to assign different IAM roles
  per user. Without role mapping, every authenticated user has the
  same permissions.

- **"The unauthenticated role is optional."** It is NOT optional if
  guest access is enabled. The unauthenticated role MUST exist and
  have minimal permissions. If guest access is enabled but the
  unauthenticated role is missing or misconfigured, guest users get
  AccessDenied errors. The unauthenticated role should be minimal
  (e.g., read-only access to specific S3 buckets) but must exist.

## Configuration dependency graph (novel heuristic)

Moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md) - load on demand (see References below).


## Expert heuristic: identity pool grants credentials, not auth

Moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md) - load on demand (see References below).


## Expert heuristic: role mapping rules evaluate JWT claims

Moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md) - load on demand (see References below).


## Expert heuristic: unauthenticated role must exist but be minimal

Moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md) - load on demand (see References below).


## Prerequisites (verify before provisioning)

Before emitting provisioning commands, verify these prerequisites. If
any are missing, the verdict is **PREREQUISITES_MISSING**.

| Prerequisite | Why it matters | How to verify |
|---|---|---|
| Identity provider exists (User Pool / SAML / OIDC) | Identity pool federates from an existing provider | `aws cognito-idp describe-user-pool --user-pool-id <id>` |
| Provider client ID / app ID known | Identity pool maps provider by client ID | Confirm client ID from provider config |
| IAM authenticated role designed | Pool grants credentials via this role | Define role permissions and trust policy |
| IAM unauthenticated role designed (if guest access) | Guest users need a role | Define minimal permissions |
| Role mapping strategy decided (token-based or rules-based) | Determines IAM role assignment | Confirm mapping approach |
| SAML provider ARN (if SAML federation) | SAML trust policy references IAM SAML provider | `aws iam get-saml-provider --saml-provider-arn <arn>` |
| Cognito service principal trust policy | Roles must be assumable by Cognito | Trust policy with cognito-identity.amazonaws.com |
| Cross-account role ARNs (if cross-account) | Multi-account federation needs role ARNs | Confirm role ARNs in target accounts |

If any prerequisite is missing, output
`VERDICT: PREREQUISITES_MISSING` and cite the specific gap.

## Step 1 — Identity pool vs user pool distinction

| Feature | Identity Pool (Federated Identities) | User Pool (User Directory) |
|---|---|---|
| Purpose | Grants AWS credentials | Authenticates users (sign-up, sign-in, MFA) |
| Stores user data | NO (delegates to provider) | YES (user directory) |
| Returns | Temporary AWS credentials (STS) | JWT tokens (ID, access, refresh) |
| Identity providers | Federates from external providers | IS a provider (for identity pools) |
| Common use | Give app users AWS access (S3, DynamoDB) | User management, authentication |

**The identity pool federates from providers.** A Cognito User Pool
can be a provider for an identity pool. Social providers (Google,
Facebook, Amazon, Apple) can also be providers. SAML and OIDC
providers can be providers.

## Step 2 — Identity providers configuration

Each identity provider maps to the identity pool via a provider name
and a client ID. The provider validates the user; the identity pool
exchanges the token for credentials.

**Supported providers:**

| Provider | Provider Name in Pool | Client ID |
|---|---|---|
| Cognito User Pool | `cognito-idp.<region>.amazonaws.com/<user-pool-id>` | User Pool app client ID |
| Amazon | `www.amazon.com` | Amazon app ID |
| Google | `accounts.google.com` | Google client ID |
| Facebook | `graph.facebook.com` | Facebook app ID |
| Apple | `appleid.apple.com` | Apple service ID |
| SAML | `arn:aws:iam::<account>:saml-provider/<name>` | SAML provider name |
| OIDC | `arn:aws:iam::<account>:oidc-provider/<name>` | OIDC client ID |

Moved verbatim to [references/providers-and-trust.md](references/providers-and-trust.md) - load on demand (see References below).


**Key fields:**
- `ProviderName` — the provider endpoint (for User Pools, the User
  Pool endpoint URL).
- `ClientId` — the app client ID registered with the provider.
- `ServerSideTokenCheck` — when true, the identity pool validates the
  token with the provider before granting credentials. Always set to
  true for production.

## Step 3 — Authenticated and unauthenticated roles

The identity pool grants credentials by assuming IAM roles via STS.
Two roles are needed:

- **Authenticated role** — for users who provide a valid provider token.
- **Unauthenticated role** — for guest users (if guest access enabled).

Moved verbatim to [references/providers-and-trust.md](references/providers-and-trust.md) and [references/worked-examples.md](references/worked-examples.md) - load on demand (see References below).



**Critical:** the `aud` condition MUST match the identity pool ID. The
`amr` condition distinguishes authenticated from unauthenticated.


## Step 4 — Role mapping (rules-based vs token-based)

Moved verbatim to [references/role-mapping-and-jwt.md](references/role-mapping-and-jwt.md) - load on demand (see References below).

### Token-based mapping (default)

All authenticated users get the same authenticated role. Simplest but
no per-user differentiation.

### Rules-based mapping

Rules evaluate JWT claims to assign different IAM roles. Each rule
specifies a claim, a match operator, a match value, and a role ARN.


**Rule evaluation order:** rules are evaluated top-to-bottom. The
first matching rule wins. If no rule matches,
`AmbiguousRoleResolution` determines the fallback (`AuthenticatedRole`
or `Deny`).

**MatchType options:**
- `Equals` — claim value equals the specified value
- `Contains` — claim value contains the specified value (for list claims)
- `NotEqual` — claim value does not equal the specified value

## Step 5 — Principal tag attribute mapping

Principal tags allow JWT claims to be passed as STS session tags,
enabling attribute-based access control (ABAC). The tags can be used
in IAM policy conditions.

Moved verbatim to [references/role-mapping-and-jwt.md](references/role-mapping-and-jwt.md) - load on demand (see References below).


This maps the `cognito:groups` claim to the `Department` session tag.
IAM policies can then use `aws:PrincipalTag/Department` for ABAC.

## Step 6 — SAML provider trust policy

For SAML federation, the IAM role trust policy must reference the IAM
SAML provider AND the identity pool.

Moved verbatim to [references/providers-and-trust.md](references/providers-and-trust.md) - load on demand (see References below).



The SAML metadata XML must be provided by the SAML IdP (e.g., Okta,
Azure AD, AD FS).

## Step 7 — Authflow: GetId + GetCredentialsForIdentity

The client-side authflow is a two-step process:

Moved verbatim to [references/worked-examples.md](references/worked-examples.md) - load on demand (see References below).


The client uses these credentials to access AWS services directly
(within the IAM role's permissions).

## Step 8 — Access control via groups and JWT claims

Cognito User Pool groups can be used for role mapping. When a user
belongs to a group, the `cognito:groups` claim in the JWT token
contains the group name.

Moved verbatim to [references/role-mapping-and-jwt.md](references/role-mapping-and-jwt.md) - load on demand (see References below).


The JWT token for this user will have
`"cognito:groups": ["admins"]`. The identity pool's rules-based
mapping evaluates this claim to assign the AdminRole.


Claims include `sub`, `email`, `cognito:groups`, `custom:attributes`,
and standard OIDC claims.

## Step 9 — Cross-account role assumption

For multi-account setups, the identity pool in Account A can assume
roles in Account B. The Account B role trust policy must allow
assumption from Account A's Cognito identity pool.

Moved verbatim to [references/role-mapping-and-jwt.md](references/role-mapping-and-jwt.md) - load on demand (see References below).


The cross-account role ARN is then referenced in the identity pool's
role mapping rules, replacing the same-account role ARN.

## Step 10 — Recent features

Moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md) - load on demand (see References below).


## NEVER do these things

1. **NEVER confuse identity pools with user pools.** Identity pools
   grant AWS credentials. User pools authenticate users. The identity
   pool federates from the user pool (or other providers). Do not try
   to configure passwords or MFA at the identity pool level.

2. **NEVER skip the unauthenticated role if guest access is enabled.**
   If `allowUnauthenticatedIdentities` is true, the unauthenticated
   role MUST exist. Missing it causes AccessDenied for guest users.

3. **NEVER give the unauthenticated role broad permissions.** The
   unauthenticated role should be minimal (read-only on specific
   resources). Guest users are unvetted — giving them write access
   is a security risk.

4. **NEVER use token-based mapping when different users need different
   roles.** Token-based mapping assigns the same role to all
   authenticated users. For per-user differentiation, use rules-based
   mapping.

5. **NEVER forget the Cognito trust policy condition keys.** The role
   trust policy MUST include `cognito-identity.amazonaws.com:aud`
   (pool ID) and `cognito-identity.amazonaws.com:amr` (authenticated/
   unauthenticated). Without these, anyone can assume the role.

6. **NEVER set ServerSideTokenCheck to false in production.** Token
   validation ensures the provider token is genuine. Disabling it
   allows forged tokens to be exchanged for AWS credentials.

7. **NEVER assume role mapping rules are evaluated randomly.** Rules
   are evaluated top-to-bottom. The first matching rule wins. Order
   matters — put more specific rules before less specific ones.

8. **NEVER hardcode JWT tokens in your application.** JWT tokens
   expire. The application must refresh tokens from the provider and
   pass fresh tokens to `GetCredentialsForIdentity`.

9. **NEVER forget cross-account trust policy for multi-account
   federation.** The target account's role MUST trust the identity
   pool's account AND have the correct ExternalId condition.

10. **NEVER use identity pools for server-to-server authentication.**
    Identity pools are for end-user federation. For server-to-server,
    use IAM roles directly (EC2 instance profiles, ECS task roles,
    or Lambda execution roles).

## Output format

```text
COGNITO_IDENTITY_POOL: <pool-name> (<pool-id>)
VERDICT: READY_TO_DEPLOY | PREREQUISITES_MISSING
CHECKLIST:
  [✓|✗] Identity pool: <pool-name> (<pool-id>)
  [✓|✗] Providers: <list of providers with client IDs>
  [✓|✗] Authenticated role: <role-arn> (trust policy: cognito-identity.amazonaws.com)
  [✓|✗] Unauthenticated role: <role-arn> (if guest access enabled)
  [✓|✗] Role mapping: Token-based | Rules-based (<rule count> rules)
  [✓|✗] Principal tags: <tag mappings or "none">
  [✓|✗] SAML provider: <provider-arn or "N/A">
  [✓|✗] Authflow: GetId + GetCredentialsForIdentity
  [✓|✗] ServerSideTokenCheck: true
  [✓|✗] Cross-account roles: <list or "same account">
  [✓|✗] Tags: <key=value list>
VERIFICATION_COMMANDS:
  aws cognito-identity describe-identity-pool --identity-pool-id <pool-id>
  aws cognito-identity get-identity-pool-roles --identity-pool-id <pool-id>
  aws iam get-role --role-name <authenticated-role>
```

### Worked example — Cognito User Pool provider with rules-based mapping

```text
COGNITO_IDENTITY_POOL: app-identity-pool (us-east-1:abcdef-1234)
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓] Identity pool: app-identity-pool (us-east-1:abcdef-1234)
  [✓] Providers: cognito-idp.us-east-1.amazonaws.com/us-east-1_AbCdEf123 (client: abc123def456)
  [✓] Authenticated role: arn:aws:iam::123456789012:role/AppAuthenticatedRole
  [✓] Unauthenticated role: arn:aws:iam::123456789012:role/AppUnauthenticatedRole
  [✓] Role mapping: Rules-based (2 rules: admins → AdminRole, readers → ReaderRole)
  [✓] Principal tags: Department ← cognito:groups
  [✓] SAML provider: N/A
  [✓] Authflow: GetId + GetCredentialsForIdentity
  [✓] ServerSideTokenCheck: true
  [✓] Cross-account roles: same account
  [✓] Tags: Environment=production, Application=app
VERIFICATION_COMMANDS:
  aws cognito-identity describe-identity-pool --identity-pool-id us-east-1:abcdef-1234
  aws cognito-identity get-identity-pool-roles --identity-pool-id us-east-1:abcdef-1234
  aws iam get-role --role-name AppAuthenticatedRole
```

## Error handling

Moved verbatim to [references/error-handling.md](references/error-handling.md) - load on demand (see References below).


## References (load on demand)

- [references/advanced-patterns.md](references/advanced-patterns.md) - dependency graph, expert heuristics, Step 10 recent features
- [references/worked-examples.md](references/worked-examples.md) - set-identity-pool-roles + authflow walkthrough
- [references/error-handling.md](references/error-handling.md) - API error deep dives (AccessDenied, mapping misses, SAML, expiry)
- [references/providers-and-trust.md](references/providers-and-trust.md) - provider setup + role trust policy templates (Steps 2/3/6)
- [references/role-mapping-and-jwt.md](references/role-mapping-and-jwt.md) - role mapping, principal tags, groups/JWT, cross-account (Steps 4/5/8/9)

## Domain

AWS CloudOps / Amazon Cognito Identity Pool Provisioning & Federated
Identity Credential Exchange.

## AWS documentation

- **Cognito Identity Pools** — https://docs.aws.amazon.com/cognito/latest/developerguide/cognito-identity.html
- **Identity pool roles** — https://docs.aws.amazon.com/cognito/latest/developerguide/role-based-access-control.html
- **Role mapping** — https://docs.aws.amazon.com/cognito/latest/developerguide/role-mapping.html
- **Identity providers** — https://docs.aws.amazon.com/cognito/latest/developerguide/external-identity-providers.html
- **SAML federation** — https://docs.aws.amazon.com/cognito/latest/developerguide/saml-identity-provider.html
- **Principal tags** — https://docs.aws.amazon.com/IAM/latest/UserGuide/id_session-tags.html
- **Cognito CLI** — https://docs.aws.amazon.com/cli/latest/reference/cognito-identity/
