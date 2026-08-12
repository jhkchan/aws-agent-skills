# Role Mapping and JWT Claims — Cognito Identity Pool Deployer

Deep reference on role mapping design (token-based vs rules-based,
rule evaluation order, AmbiguousRoleResolution), JWT claim extraction
(decoding tokens, standard and custom claims, claim-to-role matching),
and principal tag attribute mapping for ABAC. Loaded on demand by the
skill — kept out of the main SKILL.md body so the provisioning
procedure stays scannable.

## Token-based vs rules-based mapping

### Token-based (default, simple)

All authenticated users get the same role. The identity pool passes
the provider token to STS AssumeRoleWithWebIdentity with the default
authenticated role ARN.

```bash
aws cognito-identity set-identity-pool-roles \
  --identity-pool-id us-east-1:abcdef-1234 \
  --roles authenticated=arn:aws:iam::123456789012:role/AppAuthRole
```

**When to use:** all authenticated users need the same permissions.
Simplest configuration.

### Rules-based (fine-grained)

Rules evaluate JWT claims to assign different IAM roles. Each rule
has: a claim name, a match type, a match value, and a role ARN.

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
            "RoleARN": "arn:aws:iam::123456789012:role/AdminRole"
          }
          ,
          {
            "Claim": "cognito:groups",
            "MatchType": "Contains",
            "Value": "premium",
            "RoleARN": "arn:aws:iam::123456789012:role/PremiumRole"
          }
        ]
      }
    }
  }'
```

**When to use:** different users need different permissions based on
group membership, attributes, or custom claims.

### Rule evaluation order

Rules are evaluated top-to-bottom. The FIRST matching rule wins.

```text
Rule 1: cognito:groups contains "admins"   → AdminRole     ← evaluated first
Rule 2: cognito:groups contains "readers"  → ReaderRole    ← only if Rule 1 doesn't match
Fallback: AuthenticatedRole (AmbiguousRoleResolution)
```

**Key implication:** put more specific rules before less specific
ones. If a user is in both "admins" and "readers" groups, the first
rule (AdminRole) wins because it is evaluated first.

### AmbiguousRoleResolution

When no rule matches, this setting determines the fallback:

| Value | Meaning |
|---|---|
| AuthenticatedRole | Fall back to the default authenticated role |
| Deny | Deny credentials entirely |

**Use `AuthenticatedRole`** when unmatched users should get basic
access. **Use `Deny`** when unmatched users should get no AWS
credentials at all (stricter security).

### MatchType details

| MatchType | Semantics | Example |
|---|---|---|
| Equals | Claim value exactly equals | `sub == "abc-123"` |
| Contains | Claim value list contains | `cognito:groups` contains "admins" |
| NotEqual | Claim value does not equal | `custom:tier != "free"` |

**Contains** is used for list-type claims (like `cognito:groups`).
**Equals** is used for scalar claims (like `sub` or `email`).

## JWT claim extraction

### Decoding a JWT token

A JWT has three parts: header, payload, signature. The payload
(middle part) contains the claims.

```bash
# Decode JWT payload (base64url decode)
echo "<jwt-token>" | cut -d'.' -f2 | base64 -d 2>/dev/null | jq .
```

### Standard Cognito User Pool claims

```json
{
  "sub": "a1b2c3d4-...",
  "aud": "abc123def456",
  "iss": "https://cognito-idp.us-east-1.amazonaws.com/us-east-1_AbCdEf123",
  "cognito:groups": ["admins", "premium"],
  "cognito:username": "user@example.com",
  "email": "user@example.com",
  "email_verified": "true",
  "custom:division": "engineering",
  "custom:tier": "paid",
  "iat": 1723353600,
  "exp": 1723357200,
  "token_use": "id"
}
```

### Claims commonly used in role mapping

| Claim | Type | Example | Mapping use case |
|---|---|---|---|
| cognito:groups | List | ["admins", "readers"] | Group-based role assignment |
| custom:tier | String | "paid" | Tier-based access |
| custom:division | String | "engineering" | ABAC tag mapping |
| email_verified | String | "true" | Only verified users |
| token_use | String | "id" | Ensure ID token (not access token) |

## Principal tag attribute mapping

Principal tags pass JWT claims as STS session tags for ABAC. The tags
can be used in IAM policy conditions via `aws:PrincipalTag/<key>`.

### Setting principal tags

Principal tags are configured within the role mapping JSON:

```json
{
  "cognito-idp.us-east-1.amazonaws.com/us-east-1_AbCdEf123": {
    "Type": "Rules",
    "AmbiguousRoleResolution": "AuthenticatedRole",
    "RulesConfiguration": {
      "Rules": [
        {
          "Claim": "cognito:groups",
          "MatchType": "Contains",
          "Value": "admins",
          "RoleARN": "arn:aws:iam::123456789012:role/AdminRole"
        }
      ]
    }
  }
}
```

For tag-based ABAC, the IAM policy on the assumed role uses the
session tags:

```json
{
  "Effect": "Allow",
  "Action": "s3:GetObject",
  "Resource": "arn:aws:s3:::data-${aws:PrincipalTag/Department}/*"
}
```

This grants access to S3 buckets dynamically named after the user's
department tag, which was mapped from the JWT claim.

## Terraform examples

```hcl
# Identity pool
resource "aws_cognito_identity_pool" "main" {
  identity_pool_name               = "app-identity-pool"
  allow_unauthenticated_identities = true

  cognito_identity_providers {
    client_id               = aws_cognito_user_pool_client.app.id
    provider_name           = "cognito-idp.us-east-1.amazonaws.com/${aws_cognito_user_pool.main.id}"
    server_side_token_check = true
  }
}

# Authenticated role
resource "aws_iam_role" "auth" {
  name = "AppAuthenticatedRole"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Principal = { Federated = "cognito-identity.amazonaws.com" }
      Action = "sts:AssumeRoleWithWebIdentity"
      Condition = {
        StringEquals = { "cognito-identity.amazonaws.com:aud" = aws_cognito_identity_pool.main.id }
        ForAnyValue:StringLike = { "cognito-identity.amazonaws.com:amr" = "authenticated" }
      }
    }]
  })
}

# Unauthenticated role
resource "aws_iam_role" "unauth" {
  name = "AppUnauthenticatedRole"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Principal = { Federated = "cognito-identity.amazonaws.com" }
      Action = "sts:AssumeRoleWithWebIdentity"
      Condition = {
        StringEquals = { "cognito-identity.amazonaws.com:aud" = aws_cognito_identity_pool.main.id }
        ForAnyValue:StringLike = { "cognito-identity.amazonaws.com:amr" = "unauthenticated" }
      }
    }]
  })
}

# Role mapping (rules-based)
resource "aws_cognito_identity_pool_roles" "main" {
  identity_pool_id = aws_cognito_identity_pool.main.id

  authenticated_role   = aws_iam_role.auth.arn
  unauthenticated_role = aws_iam_role.unauth.arn

  role_mapping {
    identity_provider = "cognito-idp.us-east-1.amazonaws.com/${aws_cognito_user_pool.main.id}"
    type              = "Rules"
    ambiguous_role_resolution = "AuthenticatedRole"

    mapping_rule {
      claim      = "cognito:groups"
      match_type = "Contains"
      value      = "admins"
      role_arn   = aws_iam_role.admin.arn
    }

    mapping_rule {
      claim      = "cognito:groups"
      match_type = "Contains"
      value      = "readers"
      role_arn   = aws_iam_role.reader.arn
    }
  }
}
```
