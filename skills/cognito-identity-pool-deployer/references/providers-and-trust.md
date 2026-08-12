# Identity Providers and Trust Policies — Cognito Identity Pool Deployer

Deep reference on identity provider configuration (Cognito User Pool,
social providers, SAML, OIDC), IAM trust policy construction for
Cognito federation, and SAML provider trust policy specifics. Loaded
on demand by the skill — kept out of the main SKILL.md body so the
provisioning procedure stays scannable.

## Identity provider configuration

### Cognito User Pool provider

The most common provider. The User Pool authenticates the user and
issues JWT tokens. The identity pool federates from the User Pool.

```bash
aws cognito-identity create-identity-pool \
  --identity-pool-name "app-pool" \
  --allow-unauthenticated-identities \
  --cognito-identity-providers \
    ProviderName=cognito-idp.us-east-1.amazonaws.com/us-east-1_AbCdEf123, \
    ClientId=abc123def456, \
    ServerSideTokenCheck=true
```

**Key fields:**
- `ProviderName`: the User Pool endpoint URL
- `ClientId`: the User Pool app client ID
- `ServerSideTokenCheck`: validates the token server-side (always true
  in production)

### Social providers (Google, Facebook, Amazon, Apple)

Social providers are configured by their provider name and app/client
ID.

```bash
aws cognito-identity create-identity-pool \
  --identity-pool-name "social-pool" \
  --allow-unauthenticated-idententities \
  --cognito-identity-providers \
    ProviderName=accounts.google.com,ClientId=1234567890-abc.apps.googleusercontent.com,ServerSideTokenCheck=true \
  --cognito-identity-providers \
    ProviderName=graph.facebook.com,ClientId=9876543210,ServerSideTokenCheck=true
```

**Provider names for social logins:**

| Provider | Name |
|---|---|
| Google | `accounts.google.com` |
| Facebook | `graph.facebook.com` |
| Amazon | `www.amazon.com` |
| Apple | `appleid.apple.com` |

### OIDC provider

For custom OIDC providers (Auth0, Okta, etc.):

```bash
# Create IAM OIDC provider first
aws iam create-open-id-connect-provider \
  --url https://oidc.example.com \
  --thumbprint-list "a1b2c3d4e5f6..." \
  --client-id-list "my-oidc-client-id"

# Then add to identity pool
# OIDC providers use: ProviderName=arn:aws:iam::<account>:oidc-provider/<name>
```

### SAML provider

For enterprise SAML federation (Okta, Azure AD, AD FS):

```bash
# Create IAM SAML provider
aws iam create-saml-provider \
  --saml-provider-name "CorpIdP" \
  --saml-metadata-document file://saml-metadata.xml

# SAML providers use: ProviderName=arn:aws:iam::<account>:saml-provider/<name>
```

## Trust policy construction

### Cognito federation trust policy

The IAM role must allow Cognito to assume it via
`sts:AssumeRoleWithWebIdentity`:

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

**Condition keys:**

| Key | Purpose |
|---|---|
| `cognito-identity.amazonaws.com:aud` | Restricts to specific identity pool |
| `cognito-identity.amazonaws.com:amr` | Restricts to authenticated or unauthenticated |
| `cognito-identity.amazonaws.com:sub` | Restricts to specific user identity ID |

**Critical:** the `aud` value MUST be the identity pool ID. This
prevents roles from being assumed by a different identity pool.

### SAML federation trust policy

For SAML, the trust policy uses `sts:AssumeRoleWithSAML`:

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

The `SAML:aud` condition ensures only requests from the correct SAML
audience can assume the role.

### Cross-account trust policy

For roles in a different account than the identity pool:

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

The `ExternalId` condition adds a layer of assurance that only the
specific identity pool can trigger the cross-account assumption.

## Authflow mechanics

### Enhanced (simplified) authflow

The client calls Cognito directly:
1. `GetId` — exchange provider token for identity ID
2. `GetCredentialsForIdentity` — exchange identity ID + token for
   AWS credentials

Cognito internally calls STS AssumeRoleWithWebIdentity. This is the
default and simplest flow.

### Basic (classic) authflow

The client calls STS directly:
1. `GetId` — get identity ID
2. `GetOpenIdToken` — get an AWS OIDC token from Cognito
3. `sts:AssumeRoleWithWebIdentity` — exchange OIDC token for AWS
   credentials

The basic flow gives more control over which role to assume (useful
for cross-account scenarios).

## Common pitfalls

### Pitfall 1: Wrong condition key for amr

```text
WRONG:  "cognito-identity.amazonaws.com:amr": "authenticated"
RIGHT:  "ForAnyValue:StringLike": { "cognito-identity.amazonaws.com:amr": "authenticated" }
```

`amr` is a list — using a simple StringEquals fails. Must use
ForAnyValue to iterate the list.

### Pitfall 2: Missing ServerSideTokenCheck

Without server-side token check, the identity pool does not validate
the provider token. Forged tokens can be exchanged for credentials.
Always set `ServerSideTokenCheck=true` in production.

### Pitfall 3: Trust policy does not match pool ID

If the `aud` condition has a different pool ID than the actual pool,
no user can get credentials. Verify the pool ID matches exactly.

### Pitfall 4: SAML metadata expired

SAML provider metadata can become stale if the IdP rotates keys.
Re-import the metadata XML when the IdP changes its certificates.
