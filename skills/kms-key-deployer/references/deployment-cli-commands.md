# Deployment CLI Commands — KMS Key Deployer

Full copy-pasteable CLI command sequence for all 10 provisioning steps.
Variables to substitute: `<region>`, `<account-id>`, `<alias-name>`,
`<admin-role>`, `<app-role>`, `<key-id>`, `<description>`.

## Step 0: Prerequisites check

```bash
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
REGION=$(aws configure get region)

# Confirm administrator role exists
aws iam get-role --role-name <admin-role>

# Confirm application (key user) role exists
aws iam get-role --role-name <app-role>

# Confirm alias is available (must be empty result)
aws kms list-aliases --query 'Aliases[?AliasName==`alias/<alias-name>`]'
```

## Step 1: Build the key policy JSON

Save the policy to a local file for clarity. The break-glass root
statement is mandatory.

```bash
cat > /tmp/key-policy.json <<'EOF'
{
  "Version": "2012-10-17",
  "Id": "key-policy-<alias-name>",
  "Statement": [
    {
      "Sid": "Enable IAM User Permissions (break-glass)",
      "Effect": "Allow",
      "Principal": { "AWS": "arn:aws:iam::<account-id>:root" },
      "Action": "kms:*",
      "Resource": "*"
    },
    {
      "Sid": "Allow access for Key Administrators",
      "Effect": "Allow",
      "Principal": { "AWS": "arn:aws:iam::<account-id>:role/<admin-role>" },
      "Action": [
        "kms:Create*",
        "kms:Describe*",
        "kms:Enable*",
        "kms:List*",
        "kms:Put*",
        "kms:Update*",
        "kms:Revoke*",
        "kms:Disable*",
        "kms:Get*",
        "kms:Delete*",
        "kms:ScheduleKeyDeletion",
        "kms:CancelKeyDeletion",
        "kms:RotateKeyOnDemand"
      ],
      "Resource": "*"
    },
    {
      "Sid": "Allow use of the key (Cryptographic operations)",
      "Effect": "Allow",
      "Principal": { "AWS": "arn:aws:iam::<account-id>:role/<app-role>" },
      "Action": [
        "kms:Encrypt",
        "kms:Decrypt",
        "kms:ReEncrypt*",
        "kms:GenerateDataKey*",
        "kms:DescribeKey"
      ],
      "Resource": "*"
    },
    {
      "Sid": "Allow attachment of persistent resources",
      "Effect": "Allow",
      "Principal": { "AWS": "arn:aws:iam::<account-id>:role/<app-role>" },
      "Action": [
        "kms:CreateGrant",
        "kms:ListGrants",
        "kms:RevokeGrant"
      ],
      "Resource": "*",
      "Condition": {
        "Bool": { "kms:GrantIsForAWSResource": "true" }
      }
    }
  ]
}
EOF

# Substitute placeholders
sed -i.bak \
  -e "s|<account-id>|${ACCOUNT_ID}|g" \
  -e "s|<admin-role>|<admin-role>|g" \
  -e "s|<app-role>|<app-role>|g" \
  -e "s|<alias-name>|<alias-name>|g" \
  /tmp/key-policy.json
```

## Step 2: Create the CMK (symmetric AES-256 default)

```bash
KEY_ID=$(aws kms create-key \
  --description "<description>" \
  --policy file:///tmp/key-policy.json \
  --origin AWS_KMS \
  --tags '[{"TagKey":"Environment","TagValue":"production"},{"TagKey":"Application","TagValue":"<alias-name>"}]' \
  --query 'KeyMetadata.KeyId' --output text)

echo "Created key: ${KEY_ID}"
```

For asymmetric / HMAC keys, add `--key-spec` and `--usage`:

```bash
# RSA 4096 for signing
aws kms create-key \
  --key-spec RSA_4096 \
  --usage SIGN_VERIFY \
  --description "<description>" \
  --policy file:///tmp/key-policy.json

# HMAC for JWT signing
aws kms create-key \
  --key-spec HMAC_256 \
  --usage GENERATE_VERIFY_MAC \
  --description "<description>" \
  --policy file:///tmp/key-policy.json
```

## Step 3: Create the alias

```bash
aws kms create-alias \
  --alias-name alias/<alias-name> \
  --target-key-id ${KEY_ID}
```

## Step 4: Enable automatic rotation (symmetric only)

```bash
# Only SYMMETRIC_DEFAULT keys support auto-rotation
aws kms enable-key-rotation --key-id ${KEY_ID}

# Verify
aws kms get-key-rotation-status --key-id ${KEY_ID}
```

## Step 5: Multi-Region replicas (if needed)

```bash
# Create the PRIMARY as multi-Region
PRIMARY_ID=$(aws kms create-key \
  --description "<description> (multi-Region primary)" \
  --multi-region \
  --policy file:///tmp/key-policy.json \
  --query 'KeyMetadata.KeyId' --output text)

# Replica in us-west-2 (uses same key material, independent policy)
aws kms replicate-key \
  --key-id arn:aws:kms:us-east-1:${ACCOUNT_ID}:key/${PRIMARY_ID} \
  --replica-region us-west-2 \
  --description "<description> (us-west-2 replica)" \
  --policy file:///tmp/replica-policy.json
```

## Step 6: CloudHSM custom key store (if needed)

```bash
# 1. CloudHSM cluster must be ACTIVE with >= 2 HSMs
aws cloudhsmv2 describe-clusters \
  --query 'Clusters[].{Id:ClusterId,State:State,Hsms:Hsms[].State}'

# 2. Create custom key store
aws kms create-custom-key-store \
  --custom-key-store-name <name>-keystore \
  --cloud-hsm-cluster-id cluster-xxx \
  --trust-anchor fileb://trust-anchor.pem \
  --key-store-admin-credentials <kmsuser-password> \
  --hsm-credentials <partition-password>

# 3. Connect it
aws kms connect-custom-key-store \
  --custom-key-store-id cks-xxx

# 4. Create key in the custom key store
aws kms create-key \
  --custom-key-store-id cks-xxx \
  --description "<description> (CloudHSM)" \
  --policy file:///tmp/key-policy.json
```

## Step 7: Tag the key

```bash
aws kms tag-resource \
  --key-id ${KEY_ID} \
  --tags '[{"TagKey":"Environment","TagValue":"production"},{"TagKey":"Application","TagValue":"<alias-name>"},{"TagKey":"Owner","TagValue":"security-team"}]'
```

## Step 8: Create a grant (for service integration)

```bash
# Grant a migration tool time-boxed Decrypt access with context constraint
aws kms create-grant \
  --key-id ${KEY_ID} \
  --grantee-principal arn:aws:iam::<account-id>:role/migration-tool \
  --operations Decrypt \
  --constraints '{"EncryptionContextSubset": {"department": "finance"}}' \
  --retiring-principal arn:aws:iam::<account-id>:role/<admin-role> \
  --name migration-tool-decrypt-grant
```

## Step 9: Cross-account access (key owner side)

```bash
# Add a statement to the key policy granting the partner account
# (note: caller account's IAM must ALSO allow)
cat > /tmp/cross-account-statement.json <<'EOF'
{
  "Sid": "Allow cross-account use by partner",
  "Effect": "Allow",
  "Principal": { "AWS": "arn:aws:iam::<partner-account-id>:root" },
  "Action": [
    "kms:Decrypt",
    "kms:DescribeKey",
    "kms:GenerateDataKey*",
    "kms:Encrypt"
  ],
  "Resource": "*"
}
EOF
```

## Step 10: Schedule deletion (with 30-day window)

```bash
# Always 30 days for production. NEVER delete a CMK without auditing
# recent Encrypt / GenerateDataKey calls in CloudTrail first.

# Audit recent usage
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=ResourceName,AttributeValue=${KEY_ID} \
  --max-results 100

# Schedule deletion (30 days, reversible during window)
aws kms schedule-key-deletion \
  --key-id ${KEY_ID} \
  --pending-window-in-days 30
```

## Post-deployment verification

```bash
# Key metadata (state, spec, usage, multi-Region, deletion window)
aws kms describe-key --key-id alias/<alias-name>

# Rotation status (true for symmetric CMKs with rotation enabled)
aws kms get-key-rotation-status --key-id alias/<alias-name>

# Key policy
aws kms get-key-policy \
  --key-id alias/<alias-name> \
  --policy-name default

# Aliases pointing to this key
aws kms list-aliases --key-id ${KEY_ID}

# Tags
aws kms list-resource-tags --key-id ${KEY_ID}

# Active grants
aws kms list-grants --key-id ${KEY_ID}

# Multi-Region replicas (if multi-Region)
aws kms list-key-rotations --key-id ${KEY_ID}
```

## Terraform equivalents

```hcl
# Symmetric CMK with rotation
resource "aws_kms_key" "this" {
  description             = "<description>"
  deletion_window_in_days = 30
  enable_key_rotation     = true
  policy                  = data.aws_iam_policy_document.key_policy.json
  tags = {
    Environment = "production"
    Application = "<alias-name>"
  }
}

resource "aws_kms_alias" "this" {
  name          = "alias/<alias-name>"
  target_key_id = aws_kms_key.this.key_id
}

# HMAC key (no auto-rotation)
resource "aws_kms_key" "hmac" {
  description             = "<description>"
  key_usage               = "GENERATE_VERIFY_MAC"
  customer_master_key_spec = "HMAC_256"
  deletion_window_in_days = 30
  # enable_key_rotation = false  # HMAC keys cannot auto-rotate
}

# Multi-Region primary + replica
resource "aws_kms_key" "primary" {
  description             = "<description> primary"
  multi_region            = true
  deletion_window_in_days = 30
  enable_key_rotation     = false  # multi-Region cannot auto-rotate
}

resource "aws_kms_replica_key" "replica" {
  description             = "<description> replica"
  primary_key_arn         = aws_kms_key.primary.arn
  deletion_window_in_days = 30
}

# Grant for service integration
resource "aws_kms_grant" "service_integration" {
  key_id            = aws_kms_key.this.key_id
  grantee_principal = "arn:aws:iam::<account-id>:role/<service-role>"
  operations        = ["Decrypt", "GenerateDataKey"]
}
```

## CloudFormation equivalents

- `AWS::KMS::Key` — `Description`, `KeySpec`, `KeyUsage`,
  `EnableKeyRotation`, `PendingWindowInDays` (7-30), `KeyPolicy`,
  `MultiRegion`.
- `AWS::KMS::Alias` — `AliasName` (with `alias/` prefix),
  `TargetKeyId`.
- `AWS::KMS::ReplicaKey` — `PrimaryKeyArn`, `KeyPolicy`,
  `PendingWindowInDays`.
- `AWS::KMS::Key` (custom key store) — `CustomKeyStoreId`, `Origin:
  AWS_CLOUDHSM`.

## Pre-flight safety checks (from SKILL.md)

- **Confirm the AWS account ID** for root break-glass:
  `aws sts get-caller-identity --query Account --output text`
- **Confirm the key administrator role exists:**
  `aws iam get-role --role-name <admin-role>`
- **Confirm the application (key user) role exists:**
  `aws iam get-role --role-name <app-role>`
- **Confirm the alias is available:**
  `aws kms list-aliases --query 'Aliases[?AliasName==`alias/<name>`]'`
- **For custom key store:** confirm CloudHSM cluster ACTIVE with >= 2 HSMs.
- **For existing keys:** capture current policy for rollback:
  `aws kms get-key-policy --key-id <key-id> --policy-name default --output text > /tmp/<key-id>-policy-backup.json`

