# Baseline (no-skill) — ou-share-with-delegated-admin

> This is the response a model produces **without** the skill definition.
> It builds the portfolio and OU share but does not verify delegated
> admin, does not cite the caller region, and does not configure the
> LAUNCH constraint with a tag condition. Generated for with-skill-vs-
> baseline comparison.

---

To create the portfolio and share with the OU:

```bash
PORTFOLIO_ID=$(aws servicecatalog create-portfolio \
  --display-name "Data Products" \
  --provider-name "Data Platform" \
  --query 'PortfolioDetail.Id' --output text)

PRODUCT_ID=$(aws servicecatalog create-product \
  --name "Aurora Reader Endpoint" \
  --owner "Data Platform" \
  --product-type CLOUD_FORMATION_TEMPLATE \
  --provisioning-artifact-parameters \
    '{"Name":"v2.1.0","Info":{"LoadTemplateFromURL":"https://s3.amazonaws.com/data-templates/aurora-reader.yaml"}}' \
  --query 'RecordDetail.ProductId' --output text)

aws servicecatalog create-constraint \
  --portfolio-id $PORTFOLIO_ID --product-id $PRODUCT_ID \
  --parameters '{"RoleArn":"arn:aws:iam::111111111111:role/sc-launch-aurora-role"}' \
  --type LAUNCH

aws servicecatalog create-portfolio-share \
  --portfolio-id $PORTFOLIO_ID \
  --organization-node Type=ORGANIZATIONAL_UNIT,Value=ou-abc1-abcdef
```

Data Platform users in the OU can now launch Aurora reader products.
