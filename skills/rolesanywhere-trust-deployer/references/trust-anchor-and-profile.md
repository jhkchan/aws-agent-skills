# Trust Anchor and Profile — Roles Anywhere Trust Deployer

Deep reference on Roles Anywhere trust anchor creation (binding an
external certificate authority to AWS IAM, CERTIFICATE_BUNDLE vs
AWS_ACM_PCA sources, immutability and rotation), profile creation
(role mapping, role-passthrough mode, session policies, managed
policies), and the three-legged trust stool (trust anchor + profile +
IAM role with correct trust policy). Loaded on demand by the skill —
kept out of the main SKILL.md body so the provisioning procedure stays
scannable.

## Trust anchor fundamentals

### What a trust anchor does

A trust anchor binds an external certificate authority (CA) to AWS IAM.
It tells AWS "trust X.509 certificates signed by this CA." Without a
trust anchor, AWS rejects all certificates from your PKI.

### Trust anchor sources

Roles Anywhere supports two CA sources:

| Source type | Description | Use case |
|---|---|---|
| `CERTIFICATE_BUNDLE` | Self-managed CA. You provide the PEM-encoded CA certificate directly. | On-prem PKI, third-party CA (DigiCert, Entrust), custom CA |
| `AWS_ACM_PCA` | AWS Private Certificate Authority. You reference the ACM PCA ARN. | AWS-native PKI managed via ACM PCA |

### Creating a trust anchor from a self-managed CA (CERTIFICATE_BUNDLE)

```bash
CA_CERT=$(cat ca-cert.pem)

TRUST_ANCHOR_ID=$(aws rolesanywhere create-trust-anchor \
  --name "prod-pki-trust-anchor" \
  --source "sourceType=CERTIFICATE_BUNDLE,sourceData={x509CertificateData=$CA_CERT}" \
  --enabled \
  --region us-east-1 \
  --query 'trustAnchor.trustAnchorId' --output text)
```

The CA certificate must be PEM-encoded. Verify before creating:

```bash
openssl x509 -in ca-cert.pem -text -noout
```

### Creating a trust anchor from AWS Private CA (AWS_ACM_PCA)

```bash
TRUST_ANCHOR_ID=$(aws rolesanywhere create-trust-anchor \
  --name "acm-pca-trust-anchor" \
  --source "sourceType=AWS_ACM_PCA,sourceData={acmPcaArn=arn:aws:acm-pca:us-east-1:123456789012:certificate-authority/12345678-1234-1234-1234-123456789012}" \
  --enabled \
  --region us-east-1 \
  --query 'trustAnchor.trustAnchorId' --output text)
```

### Trust anchor immutability

A trust anchor is immutable once created. You cannot change the CA
certificate or source type. To rotate the CA:

1. Create a new trust anchor with the new CA certificate.
2. Update profiles to reference the new trust anchor.
3. Disable (and eventually delete) the old trust anchor.

```bash
# Disable the old trust anchor
aws rolesanywhere update-trust-anchor \
  --trust-anchor-id ta-old111222 \
  --no-enabled \
  --region us-east-1

# Delete after confirming no profiles reference it
aws rolesanywhere delete-trust-anchor \
  --trust-anchor-id ta-old111222 \
  --region us-east-1
```

### Notification settings

Trust anchors support notification settings for certificate expiry
and other events:

```bash
aws rolesanywhere create-trust-anchor \
  --name "prod-pki-trust-anchor" \
  --source file://source.json \
  --notification-settings '[{"channel":"ALL","event":"CA_CERTIFICATE_EXPIRY","enabled":true}]' \
  --enabled \
  --region us-east-1
```

## Profile fundamentals

### What a profile does

A profile maps an external certificate (validated via the trust
anchor) to one or more IAM roles. Without a profile, AWS does not
know which IAM role to assume when a certificate is presented.

### Profile fields

| Field | Purpose | Required |
|---|---|---|
| `name` | Human-readable name | Yes |
| `trustAnchorId` | The trust anchor that validates the cert | Yes |
| `roleArns` | List of IAM role ARNs the cert can assume | Yes (unless using role-passthrough) |
| `durationSeconds` | Session duration (900-43200 seconds) | Yes (default: 3600) |
| `enabled` | Enable or disable the profile | Yes (default: true) |
| `sessionPolicy` | Inline session policy (further restricts permissions) | Optional |
| `managedPolicyArns` | Managed policy ARNs to apply as session policies | Optional |
| `requireInstanceProperties` | Require instance properties in the cert | Optional (default: false) |

### Creating a profile with fixed role ARNs

```bash
PROFILE_ID=$(aws rolesanywhere create-profile \
  --name "ci-runner-profile" \
  --trust-anchor-id "$TRUST_ANCHOR_ID" \
  --role-arns "arn:aws:iam::123456789012:role/RolesAnywhereCIRunner" \
  --duration-seconds 3600 \
  --enabled \
  --region us-east-1 \
  --query 'profile.profileId' --output text)
```

### Role-passthrough mode

If `roleArns` is omitted, the profile uses role-passthrough mode, where
the client specifies the role ARN at assume time.

```bash
PROFILE_ID=$(aws rolesanywhere create-profile \
  --name "dynamic-role-profile" \
  --trust-anchor-id "$TRUST_ANCHOR_ID" \
  --duration-seconds 3600 \
  --enabled \
  --region us-east-1 \
  --query 'profile.profileId' --output text)
```

**Caution:** role-passthrough mode lets the client specify any role
ARN. Use only when the client is fully trusted, or when the IAM
roles' trust policies enforce strict Conditions (e.g., requiring a
specific profile ARN).

### Session policies

Session policies further restrict the IAM role's permissions for
sessions assumed via that profile. Effective permissions = IAM role
permissions intersected with the session policy.

**Inline session policy:**

```bash
aws rolesanywhere create-profile \
  --name "restricted-ci-profile" \
  --trust-anchor-id "$TRUST_ANCHOR_ID" \
  --role-arns "arn:aws:iam::123456789012:role/RolesAnywhereCIRunner" \
  --session-policy file://session-policy.json \
  --duration-seconds 3600 \
  --enabled \
  --region us-east-1
```

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["s3:GetObject"],
      "Resource": "arn:aws:s3:::my-ci-artifacts/*"
    }
  ]
}
```

**Managed policy as session policy:**

```bash
aws rolesanywhere create-profile \
  --name "restricted-ci-profile" \
  --trust-anchor-id "$TRUST_ANCHOR_ID" \
  --role-arns "arn:aws:iam::123456789012:role/RolesAnywhereCIRunner" \
  --managed-policy-arns "arn:aws:iam::123456789012:policy/CIReadOnlySessionPolicy" \
  --duration-seconds 3600 \
  --enabled \
  --region us-east-1
```

### Session duration

The session duration controls how long the temporary credentials are
valid. Range: 900 seconds (15 minutes) to 43200 seconds (12 hours).

| Use case | Recommended duration |
|---|---|
| CI runner (short job) | 3600s (1 hour) |
| Long-running server | 43200s (12 hours) |
| Interactive debugging | 900s (15 minutes) |

The credential helper re-runs automatically when configured as a
credential process, refreshing credentials before they expire.

## The three-legged trust stool

Roles Anywhere requires three components to function. Missing any one
results in opaque `AccessDenied` failures:

```text
1. Trust anchor (binds external CA to AWS IAM)
   → "AWS trusts certificates signed by this CA"
   → Without: AWS rejects all certificates from your PKI

2. Profile (maps external certificate to IAM role)
   → "A certificate from this CA can assume these IAM roles"
   → Without: AWS does not know which role to assume

3. IAM role (with trust policy for rolesanywhere.amazonaws.com)
   → "This role can be assumed by Roles Anywhere"
   → Without: assume fails with AccessDenied
```

### Verifying all three components

```bash
# 1. Trust anchor exists and is enabled
aws rolesanywhere list-trust-anchors --region us-east-1 \
  --query 'trustAnchors[*].{ID:trustAnchorId,Name:name,Enabled:enabled}' \
  --output table

# 2. Profile exists, references the trust anchor, and lists role ARNs
aws rolesanywhere list-profiles --region us-east-1 \
  --query 'profiles[*].{ID:profileId,Name:name,TrustAnchor:trustAnchorId,Roles:roleArns}' \
  --output table

# 3. IAM role trust policy allows rolesanywhere.amazonaws.com
aws iam get-role --role-name RolesAnywhereCIRunner \
  --query 'Role.AssumeRolePolicyDocument' --output json
```

## Terraform examples

```hcl
# Trust anchor (self-managed CA)
resource "aws_rolesanywhere_trust_anchor" "external" {
  name    = "prod-pki-trust-anchor"
  enabled = true

  source {
    source_type = "CERTIFICATE_BUNDLE"
    source_data {
      x509_certificate_data = file("ca-cert.pem")
    }
  }

  notification_settings {
    channel = "ALL"
    event   = "CA_CERTIFICATE_EXPIRY"
    enabled = true
  }
}

# Profile (maps cert to IAM role)
resource "aws_rolesanywhere_profile" "ci_runner" {
  name             = "ci-runner-profile"
  trust_anchor_id  = aws_rolesanywhere_trust_anchor.external.id
  role_arns        = [aws_iam_role.roles_anywhere.arn]
  duration_seconds = 3600
  enabled          = true
}

# IAM role with Roles Anywhere trust policy
resource "aws_iam_role" "roles_anywhere" {
  name = "RolesAnywhereCIRunner"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "rolesanywhere.amazonaws.com"
        }
        Action = "sts:AssumeRole"
        Condition = {
          StringEquals = {
            "aws:SourceProfileArn" = aws_rolesanywhere_profile.ci_runner.arn
          }
        }
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "s3_readonly" {
  role       = aws_iam_role.roles_anywhere.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonS3ReadOnlyAccess"
}
```
