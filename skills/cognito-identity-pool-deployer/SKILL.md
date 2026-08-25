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

Identity Pool configurations are NOT independent. The identity pool
must exist before providers are configured. Authenticated and
unauthenticated roles must exist before the pool can grant
credentials. Role mapping rules require roles to exist first. Use
this graph to sequence provisioning.

| Configuration | Hard dependencies (API error without) | Silent failure / immutability | Enables downstream |
|---|---|---|---|
| Identity pool | None (creates an empty pool) | pool is created with allowUnauthenticatedIdentities flag | identity provider config, role mapping |
| Authenticated role | IAM role with Cognito trust policy exists | trust policy must allow cognito-identity.amazonaws.com to assume | credentials for authenticated users |
| Unauthenticated role | IAM role with Cognito trust policy exists (if guest access) | MUST exist if pool allows unauthenticated identities | credentials for guest users |
| Identity provider | Identity pool exists; provider ARN/ID known | provider must be configured with correct client ID and provider name | token exchange for that provider |
| Role mapping (rules-based) | Identity pool exists; multiple IAM roles exist; provider configured | rules evaluate JWT claims; matching assigns IAM role | per-user IAM role assignment |
| Principal tag mapping | Identity pool exists; role mapping or default role configured | tags are injected into STS session for ABAC | attribute-based access control |
| SAML trust policy | IAM role exists; SAML provider in IAM exists | trust policy must list SAML provider and pool as principals | SAML federated access |

**The role-mapping-before-roles row is the one a baseline model
misses.** Rules-based role mapping references IAM role ARNs. If those
roles do not exist or do not have the correct trust policy, the
mapping fails silently — users fall back to the default authenticated
role, which may have wrong permissions. The procedure below forces
explicit role creation before mapping.

**Cross-dependency gotchas:**
- The identity pool grants credentials by assuming an IAM role via
  STS. The role's trust policy MUST allow `cognito-identity.amazonaws.com`
  with the `sts:AssumeRoleWithWebIdentity` action and the correct
  condition keys (`cognito-identity.amazonaws.com:aud` and
  `cognito-identity.amazonaws.com:amr`).
- Role mapping rules are evaluated in order. The first matching rule
  wins. If no rule matches, the default authenticated role is used.
- Principal tags from role mapping are passed as STS session tags.
  These tags can be used in IAM policy conditions for ABAC.
- Cross-account role assumption requires the role trust policy to
  include the identity pool's account as a trusted principal.

## Expert heuristic: identity pool grants credentials, not auth

A baseline model treats the identity pool as an authentication system.
The correct heuristic recognizes that the identity pool is a credential
exchange — it receives a token from an external provider and returns
AWS temporary credentials.

```text
Authentication flow (where auth happens):
  User → enters credentials at Provider (User Pool / Google / SAML IdP)
  Provider → validates credentials → returns JWT token

Federation flow (where identity pool works):
  Client → calls GetId (identity pool) with provider token
  Identity Pool → validates token with provider
  Identity Pool → returns identity ID

  Client → calls GetCredentialsForIdentity (identity pool) with identity ID
  Identity Pool → evaluates role mapping rules
  Identity Pool → calls STS AssumeRoleWithWebIdentity
  STS → returns temporary AWS credentials (AccessKey, SecretKey, SessionToken)
  Client → uses credentials to access AWS services
```

**Key implication:** the identity pool NEVER sees the user's password.
It only sees the provider's JWT token. This is why the identity pool
is called "federated identity" — it federates identities from external
providers into AWS.

## Expert heuristic: role mapping rules evaluate JWT claims

A baseline model assigns one role to all authenticated users. The
correct heuristic recognizes that role mapping rules can evaluate JWT
claims (like `cognito:groups`, `custom:role`, or SAML attributes) to
assign different IAM roles per user.

```text
Token-based mapping (default):
  Any authenticated user → default authenticated role

Rules-based mapping (custom):
  JWT claim: cognito:groups contains "admins"  → admin IAM role
  JWT claim: cognito:groups contains "readers" → reader IAM role
  No matching rule → default authenticated role (fallback)

Rules are evaluated in order:
  Rule 1: if claim "cognito:groups" == "admins" → arn:aws:iam::...:role/AdminRole
  Rule 2: if claim "cognito:groups" == "readers" → arn:aws:iam::...:role/ReaderRole
  Fallback → default authenticated role
```

**Key implication:** rules-based mapping is the mechanism for
fine-grained AWS access control based on user attributes. Without it,
all authenticated users get the same permissions. The JWT claims come
from the provider (User Pool groups, SAML attributes, OIDC scopes).

## Expert heuristic: unauthenticated role must exist but be minimal

A baseline model may skip the unauthenticated role. The correct
heuristic recognizes that if guest access is enabled, the unauthenticated
role MUST exist, but with minimal permissions.

```text
Unauthenticated role design:
  Permissions: minimal (e.g., read one S3 bucket, one DynamoDB table)
  NOT: full S3 access, DynamoDB full access, or any write to critical resources

Example unauthenticated policy:
  - s3:GetObject on arn:aws:s3:::public-assets/*
  - dynamodb:GetItem on arn:aws:dynamodb:...:table/public-config

Authenticated role design:
  Permissions: appropriate for authenticated users
  May vary per user via rules-based role mapping
```

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

**Create an identity pool with a Cognito User Pool provider:**

```bash
aws cognito-identity create-identity-pool \
  --identity-pool-name "app-identity-pool" \
  --allow-unauthenticated-identities \
  --cognito-identity-providers \
    ProviderName=cognito-idp.us-east-1.amazonaws.com/us-east-1_AbCdEf123, \
    ClientId=abc123def456, \
    ServerSideTokenCheck=true
```

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

**Authenticated role trust policy:**

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Federated": "cognito-identity.amazonaws.com"
      },
      "Action": "sts:AssumeRoleWithWebIdentity",
      "Condition": {
        "StringEquals": {
          "cognito-identity.amazonaws.com:aud": "us-east-1:abcdef-1234"
        },
        "ForAnyValue:StringLike": {
          "cognito-identity.amazonaws.com:amr": "authenticated"
        }
      }
    }
  ]
}
```

**Unauthenticated role trust policy:**

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Federated": "cognito-identity.amazonaws.com"
      },
      "Action": "sts:AssumeRoleWithWebIdentity",
      "Condition": {
        "StringEquals": {
          "cognito-identity.amazonaws.com:aud": "us-east-1:abcdef-1234"
        },
        "ForAnyValue:StringLike": {
          "cognito-identity.amazonaws.com:amr": "unauthenticated"
        }
      }
    }
  ]
}
```

**Critical:** the `aud` condition MUST match the identity pool ID. The
`amr` condition distinguishes authenticated from unauthenticated.

**Set the roles on the identity pool:**

```bash
aws cognito-identity set-identity-pool-roles \
  --identity-pool-id us-east-1:abcdef-1234 \
  --roles authenticated=arn:aws:iam::123456789012:role/AppAuthenticatedRole,unauthenticated=arn:aws:iam::123456789012:role/AppUnauthenticatedRole
```

## Step 4 — Role mapping (rules-based vs token-based)

### Token-based mapping (default)

All authenticated users get the same authenticated role. Simplest but
no per-user differentiation.

### Rules-based mapping

Rules evaluate JWT claims to assign different IAM roles. Each rule
specifies a claim, a match operator, a match value, and a role ARN.

```bash
aws cognito-identity set-identity-pool-roles \
  --identity-pool-id us-east-1:abcdef-1234 \
  --roles authenticated=arn:aws:iam::123456789012:role/AppDefaultRole \
  --role-mappings '{
    "cognito-idp.us-east-1.amazonaws.com/us-east-1_AbCdEf123": {
      "Type": "Rules",
      "AmbiguousRoleResolution": "AuthenticatedRole",
      "RulesConfiguration": {
        "Rules": [
          {
            "Claim": "cognito:groups",
            "MatchType": "Contains",
            "Value": "admins",
            "RoleARN": "arn:aws:iam::123456789012:role/AppAdminRole"
          },
          {
            "Claim": "cognito:groups",
            "MatchType": "Contains",
            "Value": "readers",
            "RoleARN": "arn:aws:iam::123456789012:role/AppReaderRole"
          }
        ]
      }
    }
  }'
```

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

**Enable principal tag mapping via role mapping:**

```bash
aws cognito-identity set-identity-pool-roles \
  --identity-pool-id us-east-1:abcdef-1234 \
  --roles authenticated=arn:aws:iam::123456789012:role/AppABACRole \
  --role-mappings '{
    "cognito-idp.us-east-1.amazonaws.com/us-east-1_AbCdEf123": {
      "Type": "Token",
      "AmbiguousRoleResolution": "AuthenticatedRole"
    }
  }'
```

For ABAC, the IAM role's trust policy must include tag conditions:

```json
{
  "Condition": {
    "StringEquals": {
      "aws:RequestTag/Department": "${cognito-identity.amazonaws.com:groups}"
    }
  }
}
```

This maps the `cognito:groups` claim to the `Department` session tag.
IAM policies can then use `aws:PrincipalTag/Department` for ABAC.

## Step 6 — SAML provider trust policy

For SAML federation, the IAM role trust policy must reference the IAM
SAML provider AND the identity pool.

**SAML authenticated role trust policy:**

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Federated": "arn:aws:iam::123456789012:saml-provider/CorpIdP"
      },
      "Action": "sts:AssumeRoleWithSAML",
      "Condition": {
        "StringEquals": {
          "SAML:aud": "https://signin.aws.amazon.com/saml"
        }
      }
    }
  ]
}
```

**Create IAM SAML provider:**

```bash
aws iam create-saml-provider \
  --saml-provider-name "CorpIdP" \
  --saml-metadata-document file://saml-metadata.xml
```

The SAML metadata XML must be provided by the SAML IdP (e.g., Okta,
Azure AD, AD FS).

## Step 7 — Authflow: GetId + GetCredentialsForIdentity

The client-side authflow is a two-step process:

**Step 1: GetId** — exchange the provider token for an identity ID.

```bash
aws cognito-identity get-id \
  --identity-pool-id us-east-1:abcdef-1234 \
  --logins '{"cognito-idp.us-east-1.amazonaws.com/us-east-1_AbCdEf123":"<id-token-jwt>"}'
```

**Step 2: GetCredentialsForIdentity** — exchange the identity ID for
AWS credentials.

```bash
aws cognito-identity get-credentials-for-identity \
  --identity-id us-east-1:abcdef-1234:uuid \
  --logins '{"cognito-idp.us-east-1.amazonaws.com/us-east-1_AbCdEf123":"<id-token-jwt>"}'
```

This returns temporary AWS credentials:

```json
{
  "Credentials": {
    "AccessKeyId": "ASIA...",
    "SecretKey": "...",
    "SessionToken": "...",
    "Expiration": "2026-08-11T20:00:00Z"
  }
}
```

The client uses these credentials to access AWS services directly
(within the IAM role's permissions).

## Step 8 — Access control via groups and JWT claims

Cognito User Pool groups can be used for role mapping. When a user
belongs to a group, the `cognito:groups` claim in the JWT token
contains the group name.

**User Pool groups setup:**

```bash
# Create groups in the User Pool
aws cognito-idp create-group \
  --user-pool-id us-east-1_AbCdEf123 \
  --group-name "admins"

aws cognito-idp create-group \
  --user-pool-id us-east-1_AbCdEf123 \
  --group-name "readers"

# Add users to groups
aws cognito-idp admin-add-user-to-group \
  --user-pool-id us-east-1_AbCdEf123 \
  --username "user@example.com" \
  --group-name "admins"
```

The JWT token for this user will have
`"cognito:groups": ["admins"]`. The identity pool's rules-based
mapping evaluates this claim to assign the AdminRole.

**Extracting JWT claims:**

The JWT ID token contains claims that can be decoded (base64) to
extract user attributes:

```bash
# Decode the JWT payload (middle segment)
echo "<id-token-jwt>" | cut -d'.' -f2 | base64 -d | jq .
```

Claims include `sub`, `email`, `cognito:groups`, `custom:attributes`,
and standard OIDC claims.

## Step 9 — Cross-account role assumption

For multi-account setups, the identity pool in Account A can assume
roles in Account B. The Account B role trust policy must allow
assumption from Account A's Cognito identity pool.

**Cross-account role trust policy (in Account B):**

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "AWS": "arn:aws:iam::123456789012:root"
      },
      "Action": "sts:AssumeRole",
      "Condition": {
        "StringEquals": {
          "sts:ExternalId": "us-east-1:abcdef-1234"
        }
      }
    }
  ]
}
```

The cross-account role ARN is then referenced in the identity pool's
role mapping rules, replacing the same-account role ARN.

## Step 10 — Recent features

**Recent AWS features (2023-2026):**

- **Cognito Identity Pool principal tag passthrough (2023-2024):**
  Enhanced support for passing arbitrary JWT claims as STS session
  tags for ABAC, including nested OIDC custom claims.

- **Enhanced OIDC provider support (2023-2024):** Additional OIDC
  provider configurations, including Auth0, Okta, and custom OIDC
  IdPs with discovery endpoints.

- **CloudTrail logging for GetCredentialsForIdentity (2023-2024):**
  STS AssumeRoleWithWebIdentity events now include Cognito identity
  pool metadata for better audit trail visibility.

- **Terraform provider improvements (2023-2024):** The Terraform
  `aws_cognito_identity_pool` and `aws_cognito_identity_pool_roles`
  resources now support full role mapping configuration inline,
  reducing the need for external role mapping API calls.

- **SAML attribute mapping enhancements (2024-2025):** Improved
  SAML attribute-to-principal-tag mapping, supporting multi-valued
  SAML attributes for group-based role assignment.

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

### AccessDenied when calling GetCredentialsForIdentity
- The authenticated role trust policy is missing or incorrect. Verify
  `cognito-identity.amazonaws.com:aud` matches the pool ID and
  `cognito-identity.amazonaws.com:amr` includes "authenticated".

### Guest users get AccessDenied
- The unauthenticated role does not exist or has the wrong trust
  policy. Verify the role exists and the `amr` condition includes
  "unauthenticated".

### Role mapping rules not matching
- The JWT claim may not exist or may have a different name. Decode the
  JWT token and verify the claim name and value. For Cognito User Pool
  groups, the claim is `cognito:groups`.

### SAML federation fails
- The SAML provider metadata may be stale. Re-import the metadata XML.
  Verify the SAML `aud` condition matches the expected audience.

### Expired credentials
- AWS credentials from the identity pool expire (typically 1 hour).
  The client must call `GetCredentialsForIdentity` again with a fresh
  provider token. Ensure token refresh is implemented.

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
