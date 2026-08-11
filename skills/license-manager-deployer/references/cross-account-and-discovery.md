# Cross-Account Sharing and SSM Discovery — License Manager Deployer

Deep reference on cross-account license sharing via AWS Organizations
(enablement steps, delegated administrator, OU/account sharing), SSM-
based automated discovery (on-premises managed instances, inventory
configuration), and self-service portal grants. Loaded on demand by
the skill — kept out of the main SKILL.md body so the provisioning
procedure stays scannable.

## Cross-account sharing via Organizations

### Organizations prerequisites

Cross-account license sharing requires AWS Organizations with all-
features enabled. Consolidated billing only is NOT sufficient.

```bash
# Verify Organization feature set (must be ALL)
aws organizations describe-organization \
  --query 'Organization.[FeatureSet,Id.RootId]' --output text

# Enable License Manager as a trusted service in Organizations
aws organizations enable-aws-service-access \
  --service-principal license-manager.amazonaws.com

# Verify service access
aws organizations list-aws-service-access-for-organization \
  --query 'EnabledServicePrincipals[?ServicePrincipal==`license-manager.amazonaws.com`]'
```

### Delegated administrator

The delegated administrator is the account that manages License Manager
on behalf of the Organization. This separates license management from
the Organizations management account (least privilege).

```bash
# Register a delegated administrator
aws organizations register-delegated-administrator \
  --account-id 999999999999 \
  --service-principal license-manager.amazonaws.com

# Verify delegated administrator
aws organizations list-delegated-administrators \
  --service-principal license-manager.amazonaws.com
```

**From the delegated administrator account**, all license management
operations are performed. The management account delegates full control
of License Manager to this account.

### Sharing flow

Once Organizations is enabled and a delegated administrator is
registered, license configurations can be shared.

#### Share to specific accounts

```bash
aws license-manager create-license-configuration-cross-account \
  --license-configuration-arn "$LIC_CONFIG_ID" \
  --target-organization-structure '{"Accounts":["111122223333","111122224444"]}' \
  --region us-east-1
```

For account-specific sharing, the target accounts must accept the share.
This is a request, not an automatic push.

#### Share to an Organizational Unit

```bash
aws license-manager create-license-configuration-cross-account \
  --license-configuration-arn "$LIC_CONFIG_ID" \
  --target-organization-structure '{"OrganizationalUnits":["ou-app-abcdef"]}' \
  --region us-east-1
```

For OU-based sharing, member accounts in the OU automatically receive
the shared license configuration. No per-account acceptance needed.

#### Share to the entire Organization (root OU)

```bash
aws license-manager create-license-configuration-cross-account \
  --license-configuration-arn "$LIC_CONFIG_ID" \
  --target-organization-structure '{"OrganizationalUnits":["r-xxxx"]}' \
  --region us-east-1
```

The root ID (`r-xxxx`) shares to ALL accounts in the Organization.

### Verifying cross-account sharing

```bash
# From the delegated administrator, list shared configurations
aws license-manager list-received-licenses \
  --region us-east-1

# From a member account, verify the shared config is available
aws license-manager list-received-licenses \
  --region us-east-1
```

### Common cross-account pitfalls

1. **Consolidated billing only.** The Organization feature set must be
   `ALL`, not `CONSOLIDATED_BILLING`. Check with `describe-organization`.

2. **License Manager not a trusted service.** Without
   `enable-aws-service-access`, the sharing API call fails. This is the
   #1 cross-account failure cause.

3. **Sharing from the management account instead of the delegated
   administrator.** While technically possible, this violates least-
   privilege. Use the delegated administrator.

4. **Account-specific shares not accepted.** When sharing to specific
   accounts (not OUs), the target must accept. Use OU sharing for
   automatic distribution.

## SSM managed instance discovery

### EC2 instances (automatic via association)

For EC2 instances, License Manager tracks consumption via the license
specification associated at launch. No SSM inventory needed for EC2.

```bash
# Associate at launch via run-instances
aws ec2 run-instances \
  --image-id ami-xxx \
  --instance-type m5.2xlarge \
  --license-specifications "LicenseConfigurationArn=$LIC_CONFIG_ID" \
  --region us-east-1

# Associate via launch template
aws ec2 create-launch-template \
  --launch-template-name oracle-template \
  --launch-template-data '{
    "ImageId":"ami-xxx",
    "InstanceType":"m5.2xlarge",
    "LicenseSpecifications":[{"LicenseConfigurationArn":"'"$LIC_CONFIG_ID"'"}]
  }'

# Associate with an existing AMI (inherits to all instances launched from it)
aws license-manager associate-license-to-ami \
  --license-configuration-arn "$LIC_CONFIG_ID" \
  --resource-id ami-xxx
```

### On-premises and SSM managed instances

For on-premises servers or non-EC2 resources, SSM managed instances
with inventory enabled are REQUIRED for License Manager discovery.

#### Step 1: Activate the on-prem server as a managed instance

```bash
# Create a managed-instance activation
ACTIVATION=$(aws ssm create-activation \
  --iam-role SSMServiceRole \
  --registration-limit 100 \
  --region us-east-1)

# The activation code and ID are used on the on-prem server
# Server runs: amazon-ssm-agent --register --code xxx --id xxx --region us-east-1
```

#### Step 2: Configure SSM inventory association

```bash
# Create an SSM association that collects inventory data
aws ssm create-association \
  --name AWS-InventoryManagement \
  --targets "Key=instanceids,Values=mi-xxx" \
  --schedule-expression "rate(30 minutes)" \
  --parameters '{"plugins":["Aws:InstanceInformation","Aws:SoftwareInventory"]}' \
  --region us-east-1
```

The `Aws:SoftwareInventory` plugin collects installed software data,
which License Manager reads to discover licensed applications.

#### Step 3: Configure License Manager discovery settings

```bash
# Enable License Manager integration with SSM
aws license-manager update-service-settings \
  --organization-configuration '{"EnableIntegration":true}' \
  --region us-east-1

# Verify discovery is enabled
aws license-manager get-service-settings \
  --query 'OrganizationConfiguration.EnableIntegration' \
  --region us-east-1
```

#### Step 4: Verify discovery

```bash
# List discovered resources
aws license-manager list-discovered-resources \
  --resource-type "Server" \
  --region us-east-1

# List SSM managed instances with inventory
aws ssm get-inventory \
  --query 'Entities[*].{Id:Id,Type:Data.\"AWS:InstanceInformation\".Content[0].ResourceType}' \
  --region us-east-1
```

### Common discovery pitfalls

1. **SSM agent not running on on-prem.** The SSM agent must be installed
   and running on the on-prem server, with valid activation credentials.

2. **Inventory association missing Applications collection.** The SSM
   inventory association MUST include `Aws:SoftwareInventory` plugin,
   otherwise License Manager cannot discover installed software.

3. **License Manager discovery not enabled.** The
   `update-service-settings --organization-configuration
   EnableIntegration=true` call is required. Without it, License
   Manager does not read SSM inventory.

4. **Stopped instances.** License Manager counts consumption from
   running instances. Stopped instances do NOT count, but the
   association persists.

## Self-service portal grants

Grants allow delegated users (principals) to consume licenses without
direct access to the license configuration console.

### Create a grant

```bash
aws license-manager create-grant \
  --grant-name "dev-team-oracle-grant" \
  --license-configuration-arn "$LIC_CONFIG_ID" \
  --principals '["arn:aws:iam::123456789012:role/DevTeamRole"]' \
  --allowed-operations '["CreateGrant","CheckoutLicense","ViewGrant","ListLicenses"]' \
  --region us-east-1
```

### Allowed operations

| Operation | Effect |
|---|---|
| `CreateGrant` | Recipient can create sub-grants (delegate further) |
| `CheckoutLicense` | Recipient can consume licenses |
| `ViewGrant` | Recipient can view the grant details |
| `ListLicenses` | Recipient can list available licenses |

### Grant with expiry (recommended for temporary access)

```bash
aws license-manager create-grant \
  --grant-name "contractor-grant-30d" \
  --license-configuration-arn "$LIC_CONFIG_ID" \
  --principals '["arn:aws:iam::123456789012:role/ContractorRole"]' \
  --allowed-operations '["CheckoutLicense","ViewGrant"]' \
  --expiration "2026-09-05T00:00:00Z" \
  --region us-east-1
```

**Security best practice:** always set `--expiration` for non-permanent
roles. Grants without expiry create permanent access that is easy to
forget and hard to audit.

### List and revoke grants

```bash
# List grants
aws license-manager list-grants \
  --region us-east-1

# Revoke a grant
aws license-manager delete-grant \
  --grant-arn arn:aws:license-manager:... \
  --status DISABLED \
  --region us-east-1
```

## Terraform cross-account example

```hcl
# Delegated administrator (run from management account)
resource "aws_organizations_delegated_administrators" "license_manager" {
  account_id        = "999999999999"
  service_principal = "license-manager.amazonaws.com"
}

# License configuration (run from delegated administrator account)
resource "aws_licensemanager_license_configuration" "shared" {
  provider               = aws.delegated_admin
  name                   = "org-shared-license"
  license_counting_type  = "vCPU"
  license_count          = 500
  license_rules          = ["Tenancy=Shared", "HonorVcpuOptimization=true"]
}

# Cross-account sharing (run from delegated administrator)
resource "aws_licensemanager_cross_account" "shared" {
  provider                      = aws.delegated_admin
  license_configuration_arn     = aws_licensemanager_license_configuration.shared.arn
  target_organization_structure = jsonencode({
    OrganizationalUnits = ["ou-app-abcdef"]
  })
}
```
