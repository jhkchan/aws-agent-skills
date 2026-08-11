---
description: Provision AWS Service Catalog portfolios and products with production-safe defaults — portfolio creation, product creation (CloudFormation + Terraform Open Source), versioning, constraints (LAUNCH stack/template-based, TAG_UPDATE, STACK_UPDATE, NOTIFICATION), launch paths, portfolio sharing (account, OU, organization), TagOptions, and Service App Registry integration. Emits a READY_TO_DEPLOY checklist with verification commands.
nl_triggers:
  - "create service catalog portfolio"
  - "service catalog product"
  - "service catalog launch constraint"
  - "service catalog constraint"
  - "service catalog tagoptions"
  - "portfolio share"
  - "organizational sharing"
  - "self-service launchpad"
  - "cloudformation product"
  - "terraform open source product"
  - "service app registry"
  - "service catalog delegated admin"
  - "provisioning artifact"
  - "product versioning"
routes_to: service-catalog-portfolio-deployer
---

# /aws:deploy-service-catalog-portfolio

Activate the `service-catalog-portfolio-deployer` skill and provision
Service Catalog portfolios, products, constraints, and shares with
production-safe defaults.

## What it does

The skill walks an 8-step provisioning procedure and emits a
READY_TO_DEPLOY checklist:

1. Confirm portfolio intent + consumer scope
2. Create portfolio (DisplayName, ProviderName, description)
3. Create products + provisioning artifacts (versions)
4. Associate products with the portfolio
5. Configure constraints (LAUNCH, TAG_UPDATE, STACK_UPDATE, NOTIFICATION)
6. Configure TagOptions + bind to portfolio/products
7. Configure launch paths + portfolio shares (account, OU, org)
8. Verify via `search-products` + `describe-portfolio` + emit checklist

Supported constraint types: LAUNCH (STACK-based or TEMPLATE-based),
TAG_UPDATE, STACK_UPDATE, NOTIFICATION, LAUNCH_PERMISSION.
Supported product types: CLOUD_FORMATION_TEMPLATE, TERRAFORM_OPEN_SOURCE.
Supported share types: ACCOUNT, ORGANIZATIONAL_UNIT, ORGANIZATION.

## When to use

- You are building a self-service launchpad for platform products.
- You want a governed CloudFormation or Terraform product distribution.
- You need a LAUNCH constraint pinned to a least-privilege role.
- You want to share a portfolio with an OU or the entire organization.
- You need TagOptions to suggest tags at product launch time.
- You want to integrate Service Catalog with Service App Registry.

## How to invoke

### Slash command

```
/aws:deploy-service-catalog-portfolio
```

Then provide: portfolio name, provider name, products (name +
template URL + version), constraints, TagOptions, and share target.

### Natural language

Any of these routes to the same skill:

- "create a service catalog portfolio with a curated S3 product"
- "set up a self-service launchpad"
- "share a portfolio with an organizational unit"
- "configure a launch constraint on a service catalog product"
- "publish a terraform open source service catalog product"

### CLI routing

```bash
node cli/bin/cli.js route "create service catalog portfolio"
```

## Pipeline integration

This skill operates in **Phase 1 (Deploy)** of the CloudOps pipeline.
The orchestrator routes to it when the user wants to create or update
a Service Catalog portfolio. The output checklist feeds into
verification pipelines and into operate skills (launch/update/
terminate product) and audit skills (portfolio drift detection).

## Example

```
You: /aws:deploy-service-catalog-portfolio

     Build a Service Catalog portfolio called Curated S3 Products
     with a single S3-bucket product. LAUNCH constraint with
     sc-launch-s3-role, TAG_UPDATE NOT_ALLOWED, NOTIFICATION
     sc-launch-events SNS, TagOptions CostCenter and Owner.
     Local account only.

Skill:
  PORTFOLIO: Curated S3 Products (products: 1, shares: local account only in us-east-1)
  VERDICT: READY_TO_DEPLOY
  CHECKLIST:
    [✓] Intent + consumer scope: Distribute curated S3-bucket product to local-account platform users, scope local
    [✓] Portfolio created: Curated S3 Products by Platform Governance (us-east-1)
    [✓] Product(s): 1 product (Curated S3 Bucket), 1 provisioning artifact (v1.0.0 active)
    [✓] Product-portfolio association: 1 association (Curated S3 Bucket -> Curated S3 Products)
    [✓] Constraint(s): LAUNCH sc-launch-s3-role (STACK-based, scoped to s3:* + iam:PassRole with tag condition), TAG_UPDATE NOT_ALLOWED, NOTIFICATION sc-launch-events SNS topic
    [✓] TagOptions: 2 key-value pairs bound at portfolio level (CostCenter=platform-1234, Owner=platform-governance)
    [✓] Share(s): local account only (region: us-east-1, no cross-account share configured)
  VERIFICATION_COMMANDS:
    aws servicecatalog describe-portfolio --id port-aaaa1111
    aws servicecatalog search-products-as-admin --portfolio-id port-aaaa1111
    aws servicecatalog describe-constraint --id cons-bbbb2222
    aws servicecatalog list-tag-options
    aws iam get-role --role-name sc-launch-s3-role
    ...
```

## References

- Skill definition: `skills/service-catalog-portfolio-deployer/SKILL.md`
- Constraint + launch role templates: `skills/service-catalog-portfolio-deployer/references/constraint-and-launch-role-templates.md`
- Sharing + TagOptions procedures: `skills/service-catalog-portfolio-deployer/references/sharing-and-tagoptions-procedures.md`
- Eval suite: `skills/service-catalog-portfolio-deployer/evals/evals.json`
