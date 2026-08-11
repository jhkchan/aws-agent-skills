# Baseline (no-skill) — cross-region-share-visibility-check

> This is the response a model produces **without** the skill definition.
> It applies the org-level share from us-east-1 without citing the
> region quirk, so consumers in eu-west-1 and ap-southeast-1 will not
> see the portfolio in their console and will file "missing product"
> tickets. Generated for with-skill-vs-baseline comparison.

---

Here's the multi-region portfolio shared with the org:

```bash
PORTFOLIO_ID=$(aws servicecatalog create-portfolio \
  --display-name "Multi-Region S3" \
  --provider-name "Platform Governance" \
  --query 'PortfolioDetail.Id' --output text)

PRODUCT_ID=$(aws servicecatalog create-product \
  --name "Curated S3 Bucket" \
  --owner "Platform Governance" \
  --product-type CLOUD_FORMATION_TEMPLATE \
  --provisioning-artifact-parameters \
    '{"Name":"v1.0.0","Info":{"LoadTemplateFromURL":"https://s3.amazonaws.com/platform-templates/s3-bucket.yaml"}}' \
  --query 'RecordDetail.ProductId' --output text)

aws servicecatalog create-constraint \
  --portfolio-id $PORTFOLIO_ID --product-id $PRODUCT_ID \
  --parameters '{"RoleArn":"arn:aws:iam::111111111111:role/sc-launch-s3-role"}' \
  --type LAUNCH

aws servicecatalog create-portfolio-share \
  --portfolio-id $PORTFOLIO_ID \
  --organization-node Type=ORGANIZATION,Value=o-abc123def456
```

Now all accounts in the org can launch the S3 product.
