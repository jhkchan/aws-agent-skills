# Advanced Patterns — Service Catalog Portfolio Deployer

> Moved verbatim from SKILL.md for progressive disclosure (agentskills.io). Load on demand.

## Expert heuristic: the no-LAUNCH-constraint myth

The most common misconception: "the launching user's permissions
govern what the product can deploy." They do, by default — and that
is the problem.

```text
Operator thinks:                  What actually happens:
"User launches product; their     Without a LAUNCH constraint,
permissions scope the launch."    CloudFormation assumes the user's
                                  role. A user with PowerUserAccess
                                  launches a VPC product and deploys
                                  a full VPC, NAT gateways, transit
                                  gateway attachments — all owned
                                  by their individual role. Central
                                  governance has no visibility into
                                  the resources until audit time.
```

The LAUNCH constraint is the single most important governance
primitive in Service Catalog. It pins CloudFormation to a specific
role whose permissions match ONLY the product's requirements — not
the launching user's permissions. An admin launches a curated VPC
product; the launch role has only `ec2:*` and `iam:PassRole`; the
admin cannot inject a privilege-escalation role via a template
parameter because the launch role will not pass arbitrary roles.

**The remedy is one launch role per product family** (e.g.,
`sc-launch-vpc-role`, `sc-launch-s3-role`), each scoped to only the
permissions that product family requires. Tag conditions on the
launch role add a second line of defense (e.g., the role only passes
roles tagged `sc-launch-approved=true`).


## Expert heuristic: portfolio share region quirk

A portfolio share is region-scoped. The `create-portfolio-share`
call has no region parameter — it uses the region of the calling
profile. A share to organization `o-abc123` made from a us-east-1
caller makes the portfolio visible to users in us-east-1 only. A user
in eu-west-1 will not see the portfolio in their console unless they
switch regions to us-east-1.

**For multi-region deployments:**
1. Replicate the portfolio in each region via CloudFormation
   StackSets, or
2. Document the region expectation explicitly in the portfolio
   description, or
3. Build a custom launcher (Lambda-backed) that copies the share to
   every region in scope.

The region quirk is silent — no error, the share appears to apply
"everywhere" but only resolves in one region.


## Recent AWS features

- **Service Catalog with Terraform Open Source (2024-2025):** Service
  Catalog now supports Terraform-based products in addition to
  CloudFormation. Products reference a Terraform module from a Git
  repository; Service Catalog manages `terraform apply` and state
  storage. Verify the Terraform engine is registered with Service
  Catalog in your region before publishing Terraform products.
- **Service Catalog with Terraform Cloud (2025):** integrates with
  HCP Terraform / Terraform Cloud for state management, plan
  approval, and policy-as-code (Sentinel). Useful for governance-
  heavy organizations already standardized on Terraform Cloud.
- **Service App Registry integration:** Service Catalog products can
  be associated with Service App Registry applications for unified
  application inventory. The association persists across launches,
  giving operations teams a single view of all deployed applications.
  Verify the application exists before associating.
- **CloudFormation StackSets as a Service Catalog product:** enables
  a product that, when launched, deploys a stack set across multiple
  accounts. Useful for organization-wide rollouts of governance
  primitives (Config rules, CloudTrail, etc.). Requires the launch
  role to have `cloudformation:CreateStackSet`.
- **TagOption inheritance improvements:** TagOptions bound at the
  portfolio level now propagate to all products and to all
  provisioning artifacts of those products. Verify inheritance via
  `list-tag-options` after binding.
- **Delegated administrator for Service Catalog:** allows a member
  account to manage Service Catalog portfolios on behalf of the
  organization. Verify the delegated admin is set before org-level
  shares; otherwise, member accounts can view portfolios but cannot
  manage them.
- **Service Catalog API updates:** new `update-product` and
  `update-portfolio` APIs accept a `SourceProduct` parameter for
  copying products across portfolios. Useful for promoting products
  from a staging portfolio to a production portfolio.
