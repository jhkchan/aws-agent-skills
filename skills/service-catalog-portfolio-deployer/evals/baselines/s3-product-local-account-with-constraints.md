# Baseline (no-skill) — s3-product-local-account-with-constraints

> This is the response a model produces **without** the skill definition.
> It creates the portfolio + product but omits the LAUNCH constraint
> (privilege escalation risk), uses Resource: "*" on the launch role
> PassRole, and does not configure TagOptions. Generated for with-
> skill-vs-baseline comparison.

---

To set up the Service Catalog portfolio:

```bash
PORTFOLIO_ID=$(aws servicecatalog create-portfolio \
  --display-name "Curated S3 Products" \
  --provider-name "Platform Governance" \
  --query 'PortfolioDetail.Id' --output text)

PRODUCT_ID=$(aws servicecatalog create-product \
  --name "Curated S3 Bucket" \
  --owner "Platform Governance" \
  --product-type CLOUD_FORMATION_TEMPLATE \
  --provisioning-artifact-parameters \
    '{"Name":"v1.0.0","Info":{"LoadTemplateFromURL":"https://s3.amazonaws.com/platform-templates-us-east-1/s3-bucket.yaml"}}' \
  --query 'RecordDetail.ProductId' --output text)

aws servicecatalog associate-product-with-portfolio \
  --product-id $PRODUCT_ID --portfolio-id $PORTFOLIO_ID
```

Users can launch the S3 bucket product from this portfolio.
