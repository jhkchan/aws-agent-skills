# Baseline (no-skill) — terraform-open-source-product

> This is the response a model produces **without** the skill definition.
> It attempts the Terraform product but does not verify the
> TERRAFORM_OPEN_SOURCE engine is available in us-east-1, omits the
> LAUNCH constraint with tag condition, and does not bind TagOptions
> at the portfolio level. Generated for with-skill-vs-baseline
> comparison.

---

To create a Service Catalog product from a Terraform module:

```bash
PORTFOLIO_ID=$(aws servicecatalog create-portfolio \
  --display-name "Terraform Products" \
  --provider-name "Platform Governance" \
  --query 'PortfolioDetail.Id' --output text)

PRODUCT_ID=$(aws servicecatalog create-product \
  --name "Terraform S3 Bucket" \
  --owner "Platform Governance" \
  --product-type TERRAFORM_OPEN_SOURCE \
  --provisioning-artifact-parameters \
    '{"Name":"v1.0.0","Info":{"TerraformSource":{"SourceUrl":"git::https://github.com/example/terraform-s3-bucket.git?ref=v1.0.0"}}}' \
  --query 'RecordDetail.ProductId' --output text)

aws servicecatalog associate-product-with-portfolio \
  --product-id $PRODUCT_ID --portfolio-id $PORTFOLIO_ID
```

Local users can launch the Terraform S3 bucket product.
