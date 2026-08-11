# Deployment CLI Commands — RAM Resource Share Deployer

Full copy-pasteable CLI command sequence for all 9 provisioning steps.
Variables to substitute: `<region>`, `<account-id>`, `<resource-share-name>`,
`<resource-arn>`, `<resource-type>`, `<principal>`, `<organization-id>`.

## Step 0: Prerequisites check

```bash
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
REGION=$(aws configure get region)

# Confirm Organizations all features enabled (for org/OU sharing)
aws organizations describe-organization --query 'Organization.FeatureSet' --output text

# List shareable resource types
aws ram list-resource-types

# Confirm available permissions for the resource type
aws ram list-permissions --resource-type <resource-type> --resource-owner SELF

# List existing resource shares
aws ram get-resource-shares --resource-owner SELF
```

## Step 1: Create a resource share with account ID principals

```bash
cat > /tmp/resource-share.json <<'EOF'
{
  "name": "shared-subnets-prod",
  "allowExternalPrincipals": false,
  "principals": [
    "111111111111",
    "222222222222"
  ],
  "resources": [
    {
      "arn": "arn:aws:ec2:us-east-1:123456789012:subnet/subnet-abc123",
      "type": "ec2:Subnet"
    },
    {
      "arn": "arn:aws:ec2:us-east-1:123456789012:subnet/subnet-def456",
      "type": "ec2:Subnet"
    }
  ],
  "tags": [
    { "Key": "Environment", "Value": "production" },
    { "Key": "Application", "Value": "networking" }
  ]
}
EOF

aws ram create-resource-share \
  --cli-input-json file:///tmp/resource-share.json \
  --region us-east-1
```

## Step 2: Share with Organization ARN

```bash
aws ram create-resource-share \
  --name shared-tgw-org \
  --allow-external-principals false \
  --principals arn:aws:organizations::123456789012:organization/o-abc123def \
  --resources arn=arn:aws:ec2:us-east-1:123456789012:transit-gateway/tgw-0abc123def,type=ec2:TransitGateway \
  --tags '[{"Key":"Environment","Value":"production"}]' \
  --region us-east-1
```

## Step 3: Share with OU ARN

```bash
aws ram create-resource-share \
  --name shared-resolver-rules-ou \
  --allow-external-principals false \
  --principals arn:aws:organizations::123456789012:ou/o-abc123def/ou-xyz456 \
  --resources arn=arn:aws:route53resolver:us-east-1:123456789012:resolver-rule/rslvr-rr-abc123,type=route53resolver:ResolverRule \
  --tags '[{"Key":"Environment","Value":"production"},{"Key":"Application","Value":"dns"}]' \
  --region us-east-1
```

## Step 4: Create a customer-managed permission

```bash
cat > /tmp/permission.json <<'EOF'
{
  "name": "custom-subnet-readonly",
  "resourceType": "ec2:Subnet",
  "policyTemplate": "{\"Version\":\"2012-10-17\",\"Statement\":[{\"Effect\":\"Allow\",\"Action\":[\"ec2:CreateNetworkInterface\",\"ec2:DescribeSubnets\"],\"Resource\":\"*\"}]}",
  "policyType": "MANAGED"
}
EOF

aws ram create-permission \
  --cli-input-json file:///tmp/permission.json \
  --region us-east-1

# Get the permission ARN
PERMISSION_ARN=$(aws ram list-permissions \
  --resource-type ec2:Subnet \
  --resource-owner SELF \
  --query 'permissions[?name==`custom-subnet-readonly`].arn' \
  --output text \
  --region us-east-1)
```

## Step 5: Associate a permission with a resource share

```bash
# Associate customer-managed permission
aws ram associate-resource-share-permission \
  --resource-share-arn arn:aws:ram:us-east-1:123456789012:resource-share/shared-subnets-custom-perm \
  --permission-arn ${PERMISSION_ARN} \
  --region us-east-1

# List permissions on a resource share
aws ram list-resource-share-permissions \
  --resource-share-arn arn:aws:ram:us-east-1:123456789012:resource-share/shared-subnets-prod \
  --region us-east-1
```

## Step 6: Associate additional resources

```bash
aws ram associate-resource-share \
  --resource-share-arn arn:aws:ram:us-east-1:123456789012:resource-share/shared-subnets-prod \
  --resource-arns \
    arn:aws:ec2:us-east-1:123456789012:subnet/subnet-ghi789 \
  --region us-east-1
```

## Step 7: Associate additional principals

```bash
aws ram associate-resource-share \
  --resource-share-arn arn:aws:ram:us-east-1:123456789012:resource-share/shared-subnets-prod \
  --principals 333333333333 \
  --region us-east-1
```

## Step 8: Accept resource share invitations (external only)

```bash
# On the principal account — list pending invitations
aws ram get-resource-share-invitations \
  --resource-owner OTHER-ACCOUNTS \
  --region us-east-1

# Accept the invitation
aws ram accept-resource-share \
  --resource-share-invitation-arn arn:aws:ram:us-east-1:123456789012:resource-share-invitation/abc123 \
  --region us-east-1

# Reject (if needed)
aws ram reject-resource-share \
  --resource-share-invitation-arn arn:aws:ram:us-east-1:123456789012:resource-share-invitation/abc123 \
  --region us-east-1
```

Within an Organization with all features, invitations are auto-accepted.

## Step 9: Verification and post-deployment checks

```bash
# Verify the resource share
aws ram get-resource-shares \
  --resource-share-arns arn:aws:ram:us-east-1:123456789012:resource-share/shared-subnets-prod \
  --region us-east-1

# List principals in the share
aws ram list-principals \
  --resource-owner SELF \
  --resource-share-arn arn:aws:ram:us-east-1:123456789012:resource-share/shared-subnets-prod \
  --region us-east-1

# List resources in the share
aws ram list-resources \
  --resource-owner SELF \
  --resource-share-arn arn:aws:ram:us-east-1:123456789012:resource-share/shared-subnets-prod \
  --region us-east-1

# List permission associations
aws ram list-resource-share-permissions \
  --resource-share-arn arn:aws:ram:us-east-1:123456789012:resource-share/shared-subnets-prod \
  --region us-east-1

# Promote a resource share created from a resource-based policy
aws ram promote-resource-share-created-from-policy \
  --resource-share-arn arn:aws:ram:us-east-1:123456789012:resource-share/shared-subnets-prod \
  --region us-east-1
```

## Terraform equivalents

```hcl
# Resource share
resource "aws_ram_resource_share" "subnets" {
  name                      = "shared-subnets-prod"
  allow_external_principals = false

  tags = {
    Environment = "production"
    Application = "networking"
  }
}

# Principal association (account IDs)
resource "aws_ram_principal_association" "accounts" {
  for_each = toset(["111111111111", "222222222222"])

  principal          = each.value
  resource_share_arn = aws_ram_resource_share.subnets.arn
}

# Principal association (Organization ARN)
resource "aws_ram_principal_association" "org" {
  principal          = "arn:aws:organizations::123456789012:organization/o-abc123def"
  resource_share_arn = aws_ram_resource_share.tgw.arn
}

# Principal association (OU ARN)
resource "aws_ram_principal_association" "ou" {
  principal          = "arn:aws:organizations::123456789012:ou/o-abc123def/ou-xyz456"
  resource_share_arn = aws_ram_resource_share.resolver.arn
}

# Resource association
resource "aws_ram_resource_association" "subnets" {
  for_each = toset(["subnet-abc123", "subnet-def456"])

  resource_arn       = "arn:aws:ec2:us-east-1:123456789012:subnet/${each.value}"
  resource_share_arn = aws_ram_resource_share.subnets.arn
}

# Customer-managed permission
resource "aws_ram_permission" "custom_subnet" {
  name         = "custom-subnet-readonly"
  resource_type = "ec2:Subnet"
  policy_template = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["ec2:CreateNetworkInterface", "ec2:DescribeSubnets"]
      Resource = "*"
    }]
  })
}

# Associate permission with resource share
resource "aws_ram_resource_share" "custom_perm" {
  name                      = "shared-subnets-custom-perm"
  allow_external_principals = false
  permission_arn            = aws_ram_permission.custom_subnet.arn
}
```

## CloudFormation equivalents

- `AWS::RAM::ResourceShare` — `Name`, `AllowExternalPrincipals`,
  `Principals` (account IDs, OU ARNs, Organization ARN),
  `Resources` (ARN + type pairs), `Tags`.
- No native CloudFormation resource for permission association —
  use `AWS::RAM::ResourceShare` with `Principals` and `Resources`
  embedded, or manage permissions via CLI/Terraform.
