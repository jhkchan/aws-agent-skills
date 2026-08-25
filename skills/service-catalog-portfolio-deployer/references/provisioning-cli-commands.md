# Provisioning CLI Commands — Service Catalog Portfolio Deployer

> Moved verbatim from SKILL.md for progressive disclosure (agentskills.io). Load on demand.

### Step 3 — Create products + provisioning artifacts (CLI)

```bash
PRODUCT_ID=$(aws servicecatalog create-product \
  --name "Curated S3 Bucket" \
  --owner "Platform Governance" \
  --product-type CLOUDFORMATION_TEMPLATE \
  --provisioning-artifact-parameters \
    '{"Name":"v1.0.0","Description":"Initial release","Info":{"LoadTemplateFromURL":"https://s3.amazonaws.com/platform-templates-us-east-1/s3-bucket.yaml"},"Type":"CLOUD_FORMATION_TEMPLATE"}' \
  --query 'RecordDetail.ProductId' --output text)
```

For versioned releases, create additional provisioning artifacts on
the same product:

```bash
aws servicecatalog create-provisioning-artifact \
  --product-id $PRODUCT_ID \
  --parameters file://v1-1-0.json
```
