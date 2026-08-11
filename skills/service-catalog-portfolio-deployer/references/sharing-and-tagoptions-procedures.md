# Sharing + TagOptions + App Registry Procedures — Service Catalog

Reference procedures for portfolio sharing (account, OU,
organization), TagOptions binding, App Registry integration, and
verification commands. Stored here so the main skill body stays
scannable.

## 1. Enable Service Catalog access in Organizations

```bash
aws organizations enable-aws-service-access \
  --service-principal servicecatalog.amazonaws.com

# Verify
aws organizations list-aws-services-for-organization \
  --query 'EnabledServicePrincipals[?ServicePrincipal==`servicecatalog.amazonaws.com`]'
```

Required before any org-level or OU-level share. Without this,
`create-portfolio-share --organization-node Type=ORGANIZATION` returns
`AccessDeniedException`.

## 2. Set a delegated administrator

```bash
aws organizations register-delegated-administrator \
  --account-id <ADMIN_ACCOUNT_ID> \
  --service-principal servicecatalog.amazonaws.com

# Verify
aws organizations list-delegated-administrators \
  --service-principal servicecatalog.amazonaws.com
```

The delegated administrator can manage portfolios on behalf of the
organization. Without it, member accounts can view shared portfolios
but cannot update them.

## 3. Share to a single account

```bash
aws servicecatalog create-portfolio-share \
  --portfolio-id <PORTFOLIO_ID> \
  --account-id <CONSUMER_ACCOUNT_ID>
```

Region: the share is recorded in the caller's region. A consumer in
another region will not see the portfolio in their console unless
they switch regions to the caller's region.

## 4. Share to an Organizational Unit

```bash
aws servicecatalog create-portfolio-share \
  --portfolio-id <PORTFOLIO_ID> \
  --organization-node Type=ORGANIZATIONAL_UNIT,Value=ou-abc1-abcdef

# Verify
aws servicecatalog describe-portfolio-shares \
  --portfolio-id <PORTFOLIO_ID> \
  --type ORGANIZATION
```

OU shares propagate to all child OUs and accounts. To revoke, use
`delete-portfolio-share` with the same `--organization-node`.

## 5. Share to the entire Organization

```bash
aws servicecatalog create-portfolio-share \
  --portfolio-id <PORTFOLIO_ID> \
  --organization-node Type=ORGANIZATION,Value=o-abc123def456
```

`Type=ORGANIZATION` shares to every account in the org. Use this
only for genuinely universal products (e.g., baseline
configurations); prefer OU-level shares for scoped distribution.

## 6. Cross-region replication (for multi-region deployments)

For each region in scope:

```bash
# Caller profile uses the target region
AWS_DEFAULT_REGION=eu-west-1 aws servicecatalog create-portfolio \
  --display-name "Curated S3 Products" \
  --provider-name "Platform Governance" \
  --description "S3-bucket products for analytics. Region: eu-west-1."

# Repeat product creation, associations, constraints, shares in this region
# Use CloudFormation StackSets to automate replication
```

A programmatic alternative is a CloudFormation StackSet with the
portfolio template, deployed across all target regions.

## 7. Create TagOptions

```bash
TAG_OPTION_ID=$(aws servicecatalog create-tag-option \
  --key "CostCenter" \
  --value "platform-1234" \
  --query 'TagOptionDetail.Id' --output text)

# Verify the TagOption exists
aws servicecatalog describe-tag-option --id $TAG_OPTION_ID
```

TagOption keys and values must be unique within the account. Re-
creating an existing key+value returns the existing TagOption ID.

## 8. Associate TagOptions with a portfolio (portfolio-level)

```bash
aws servicecatalog associate-tag-option-with-resource \
  --resource-id <PORTFOLIO_ID> \
  --tag-option-id $TAG_OPTION_ID
```

Portfolio-level TagOptions propagate to every product in the
portfolio at launch time. New products added to the portfolio
inherit the TagOptions automatically.

## 9. Associate TagOptions with a product (product-level)

```bash
aws servicecatalog associate-tag-option-with-resource \
  --resource-id <PRODUCT_ID> \
  --tag-option-id $TAG_OPTION_ID
```

Product-level TagOptions are scoped to that product. Use product-
level for product-specific tags (e.g., DataClassification=PII for a
database product) and portfolio-level for universal tags (e.g.,
Owner=platform-governance).

## 10. List + verify TagOptions

```bash
# All TagOptions in the account
aws servicecatalog list-tag-options

# TagOptions for a specific resource
aws servicecatalog list-tag-options \
  --filters Key=CostCenter,Value=platform-1234
```

## 11. App Registry integration

App Registry associates a Service Catalog product with an Application
in Service App Registry for unified inventory.

```bash
# Create the application first
APP_ID=$(aws servicecatalog-appregistry create-application \
  --name "analytics-s3-stack" \
  --type "ServiceCatalog" \
  --query 'application.id --output text)

# Associate the Service Catalog product with the application
aws servicecatalog-appregistry associate-resource \
  --application $APP_ID \
  --resource-type "CFN_STACK" \
  --resource <PROVISIONED_PRODUCT_STACK_ID>
```

The association persists across launches; App Registry tracks all
launched instances of the product under the application. Verify the
application exists before associating; deleted applications silently
break the association.

## 12. Consumer-side verification

To verify a portfolio share works for the consumer:

```bash
# Switch to a consumer account profile
aws servicecatalog search-products --profile consumer-profile

# The portfolio's products should be visible
aws servicecatalog list-accepted-portfolio-shares --profile consumer-profile

# Try launching the product (dry-run via describe-provisioning-parameters)
aws servicecatalog describe-provisioning-parameters \
  --product-id <PRODUCT_ID> \
  --provisioning-artifact-id <ARTIFACT_ID> \
  --path-id <LAUNCH_PATH_ID> \
  --profile consumer-profile
```

If `search-products` returns empty, the most common causes are:
1. **Region mismatch.** Consumer is in a different region from the
   share. Have them switch regions in the console.
2. **Missing delegated admin.** Consumer cannot accept the share
   without delegated administrator (rare for org-level shares; more
   common for account-level).
3. **IAM scoping.** Consumer's role lacks
   `servicecatalog:SearchProducts`. Check IAM.

## 13. Revoke a share

```bash
aws servicecatalog delete-portfolio-share \
  --portfolio-id <PORTFOLIO_ID> \
  --account-id <CONSUMER_ACCOUNT_ID>
```

For OU/org shares:

```bash
aws servicecatalog delete-portfolio-share \
  --portfolio-id <PORTFOLIO_ID> \
  --organization-node Type=ORGANIZATIONAL_UNIT,Value=ou-abc1-abcdef
```

Existing provisioned products remain; only the share is revoked. New
launches are blocked. Clean up provisioned products before revoking
the share to avoid orphan resources.

## 14. Service Catalog Terraform Open Source integration

To publish a Terraform-based product:

```bash
aws servicecatalog create-product \
  --name "Curated S3 Bucket (Terraform)" \
  --owner "Platform Governance" \
  --product-type TERRAFORM_OPEN_SOURCE \
  --provisioning-artifact-parameters \
    '{"Name":"v1.0.0","Description":"Initial Terraform release","Info":{"TerraformSource":{"SourceUrl":"git::https://github.com/example/terraform-s3-bucket.git?ref=v1.0.0"}},"Type":"TERRAFORM_OPEN_SOURCE"}'
```

Verify the Terraform engine is registered with Service Catalog:

```bash
aws servicecatalog list-provisioning-engine-types \
  --query 'ProvisioningEngineTypes'
```

If `TERRAFORM_OPEN_SOURCE` is not in the list, the region does not
support Terraform products yet. Fall back to CloudFormation or
replicate the portfolio in a region that supports Terraform.
