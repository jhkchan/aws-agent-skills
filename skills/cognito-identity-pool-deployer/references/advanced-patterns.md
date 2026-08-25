# Advanced patterns - Cognito Identity Pool Deployer (load on demand)

## Configuration dependency graph (novel heuristic) (moved from SKILL.md)

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

## Step 10 - Recent features

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

