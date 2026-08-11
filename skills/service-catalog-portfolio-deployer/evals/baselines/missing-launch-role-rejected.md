# Baseline (no-skill) — missing-launch-role-rejected

> This is the response a model produces **without** the skill definition.
> It applies the org-level share with no LAUNCH constraint, exposing
> every account in the org to a powerful VPC product that any user can
> launch with their own role. Generated for with-skill-vs-baseline
> comparison.

---

Sure, here's the portfolio with the VPC product shared to the org:

```bash
PORTFOLIO_ID=$(aws servicecatalog create-portfolio \
  --display-name "Power Tools" \
  --provider-name "Platform" \
  --query 'PortfolioDetail.Id' --output text)

PRODUCT_ID=$(aws servicecatalog create-product \
  --name "VPC Creator" \
  --owner "Platform" \
  --product-type CLOUD_FORMATION_TEMPLATE \
  --provisioning-artifact-parameters \
    '{"Name":"v1.0.0","Info":{"LoadTemplateFromURL":"https://s3.amazonaws.com/platform-templates/vpc.yaml"}}' \
  --query 'RecordDetail.ProductId' --output text)

aws servicecatalog associate-product-with-portfolio \
  --product-id $PRODUCT_ID --portfolio-id $PORTFOLIO_ID

aws servicecatalog create-portfolio-share \
  --portfolio-id $PORTFOLIO_ID \
  --organization-node Type=ORGANIZATION,Value=o-abc123def456
```

Your whole org can now launch VPCs from this portfolio.
