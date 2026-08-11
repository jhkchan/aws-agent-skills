# End-to-End Example: Service Catalog S3 Product with Constraints

A walkthrough showing how to use the `service-catalog-portfolio-
deployer` skill from invocation through verification. Mirrors the
structured-eval pattern of shipping a concrete worked example per
skill.

---

## Scenario

You are distributing a curated S3-bucket product to your platform
team via Service Catalog, in a single account. You need:

- A portfolio `Curated S3 Products` with the S3 product
- A STACK-based LAUNCH constraint pinned to `sc-launch-s3-role`
  (scoped to `s3:*` + `iam:PassRole` with tag condition)
- TAG_UPDATE constraint set to `NOT_ALLOWED`
- NOTIFICATION constraint to SNS topic `sc-launch-events`
- TagOptions: `CostCenter=platform-1234`, `Owner=platform-governance`
- Local account only (no cross-account share)

Region: us-east-1
Account: 111111111111

---

## Step 1 — Invoke the skill

### Option A: Slash command

```
/aws:deploy-service-catalog-portfolio
```

Then paste the portfolio spec.

### Option B: Natural language

```
You: "Build a Service Catalog portfolio called Curated S3 Products
      with a single S3-bucket product. LAUNCH constraint with
      sc-launch-s3-role, TAG_UPDATE NOT_ALLOWED, NOTIFICATION
      sc-launch-events SNS, TagOptions CostCenter and Owner.
      Local account only."
```

### Option C: CLI routing

```bash
node cli/bin/cli.js route "create service catalog portfolio"
```

Output:

```
[Phase: Deploy | Skills routed: service-catalog-portfolio-deployer]
Primary route: service-catalog-portfolio-deployer (score: 21)
```

---

## Step 2 — Skill produces the READY_TO_DEPLOY checklist

```text
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
```

---

## Step 3 — Provisioning commands

```bash
# Step 5 prereq: Create the launch role (with tag conditions)
aws iam create-role \
  --role-name sc-launch-s3-role \
  --assume-role-policy-document '{
    "Version":"2012-10-17",
    "Statement":[{"Effect":"Allow","Principal":{"Service":"cloudformation.amazonaws.com"},"Action":"sts:AssumeRole"}]
  }'

aws iam put-role-policy \
  --role-name sc-launch-s3-role \
  --policy-name s3-only \
  --policy-document '{
    "Version":"2012-10-17",
    "Statement":[
      {"Effect":"Allow","Action":["s3:CreateBucket","s3:PutBucketVersioning","s3:PutBucketEncryption","s3:PutBucketPolicy","s3:PutBucketTagging","s3:PutLifecycleConfiguration"],"Resource":"arn:aws:s3:::sc-launched-*"},
      {"Effect":"Allow","Action":["s3:ListBucket"],"Resource":"arn:aws:s3:::sc-launched-*"},
      {"Effect":"Allow","Action":"iam:PassRole","Resource":"*","Condition":{"StringEquals":{"aws:ResourceTag/sc-launch-approved":"true"}}}
    ]
  }'

# Step 5 prereq: SNS topic for NOTIFICATION constraint
aws sns create-topic --name sc-launch-events

# Step 2: Create portfolio
PORTFOLIO_ID=$(aws servicecatalog create-portfolio \
  --display-name "Curated S3 Products" \
  --provider-name "Platform Governance" \
  --description "S3-bucket products for analytics workloads. Launch role scoped to s3:* only. Region: us-east-1." \
  --query 'PortfolioDetail.Id' --output text)

# Step 3: Create product + initial provisioning artifact
PRODUCT_ID=$(aws servicecatalog create-product \
  --name "Curated S3 Bucket" \
  --owner "Platform Governance" \
  --product-type CLOUD_FORMATION_TEMPLATE \
  --provisioning-artifact-parameters \
    '{"Name":"v1.0.0","Description":"Initial release","Info":{"LoadTemplateFromURL":"https://s3.amazonaws.com/platform-templates-us-east-1/s3-bucket.yaml"},"Type":"CLOUD_FORMATION_TEMPLATE"}' \
  --query 'RecordDetail.ProductId' --output text)

# Step 4: Associate product with portfolio
aws servicecatalog associate-product-with-portfolio \
  --product-id $PRODUCT_ID --portfolio-id $PORTFOLIO_ID

# Step 5: Constraints (LAUNCH, TAG_UPDATE, NOTIFICATION)
aws servicecatalog create-constraint \
  --portfolio-id $PORTFOLIO_ID --product-id $PRODUCT_ID \
  --parameters '{"RoleArn":"arn:aws:iam::111111111111:role/sc-launch-s3-role","LocalRoleName":"sc-launch-s3-role"}' \
  --type LAUNCH

aws servicecatalog create-constraint \
  --portfolio-id $PORTFOLIO_ID --product-id $PRODUCT_ID \
  --parameters '{"TagUpdate":"NOT_ALLOWED"}' \
  --type TAG_UPDATE

aws servicecatalog create-constraint \
  --portfolio-id $PORTFOLIO_ID --product-id $PRODUCT_ID \
  --parameters '{"NotificationArns":["arn:aws:sns:us-east-1:111111111111:sc-launch-events"]}' \
  --type NOTIFICATION

# Step 6: TagOptions bound at portfolio level
CC_TAG=$(aws servicecatalog create-tag-option --key "CostCenter" --value "platform-1234" --query 'TagOptionDetail.Id' --output text)
OWNER_TAG=$(aws servicecatalog create-tag-option --key "Owner" --value "platform-governance" --query 'TagOptionDetail.Id' --output text)

aws servicecatalog associate-tag-option-with-resource --resource-id $PORTFOLIO_ID --tag-option-id $CC_TAG
aws servicecatalog associate-tag-option-with-resource --resource-id $PORTFOLIO_ID --tag-option-id $OWNER_TAG
```

---

## Step 4 — Post-deployment verification

```bash
# Verify portfolio exists
aws servicecatalog describe-portfolio --id $PORTFOLIO_ID

# Verify product is associated
aws servicecatalog search-products-as-admin --portfolio-id $PORTFOLIO_ID

# Verify constraints
aws servicecatalog list-constraints-for-portfolio --portfolio-id $PORTFOLIO_ID

# Verify TagOptions
aws servicecatalog list-tag-options

# Verify the launch role
aws iam get-role --role-name sc-launch-s3-role
aws iam get-role-policy --role-name sc-launch-s3-role --policy-name s3-only

# Consumer-side: a platform-team user should be able to see the product
aws servicecatalog search-products
```

---

## What the skill catches that a naive provisioning misses

| Configuration | Naive provisioning | Skill output | Why the skill is right |
|---|---|---|---|
| LAUNCH constraint | Skipped | STACK-based with sc-launch-s3-role | Without LAUNCH, CloudFormation uses the user's role — a PowerUserAccess user could deploy arbitrary S3 features owned by their individual role. The launch role pins CloudFormation to a least-privilege role regardless of who clicks Launch. |
| iam:PassRole scope | `Resource: "*"` | `Resource: "*"` with tag condition | The launch role grants iam:PassRole only to roles tagged `sc-launch-approved=true`. A malicious template parameter that tries to pass an admin role is refused at stack-create time. |
| TAG_UPDATE constraint | Skipped | `NOT_ALLOWED` | Without this, users can modify tags on the launched stack post-launch, defeating the TagOptions suggestion at launch time. |
| NOTIFICATION constraint | Skipped | SNS topic configured | Without notifications, launches happen silently — no audit trail until CloudTrail review. SNS events give real-time visibility. |
| TagOptions binding | None | Bound at portfolio level | Portfolio-level TagOptions propagate to every product added to the portfolio, including future products. Product-level TagOptions are scoped and miss future additions. |
| Template URL validation | Skipped | `validate-template` confirmed | A broken URL passes `create-product` (Service Catalog does not fetch the template) and fails at consumer launch time with no admin-side signal. |

---

## Related artifacts

- **Skill definition:** `skills/service-catalog-portfolio-deployer/SKILL.md`
- **Constraint + launch role templates:** `skills/service-catalog-portfolio-deployer/references/constraint-and-launch-role-templates.md`
- **Sharing + TagOptions procedures:** `skills/service-catalog-portfolio-deployer/references/sharing-and-tagoptions-procedures.md`
- **Slash command:** `commands/aws/deploy-service-catalog-portfolio.md`
- **Eval suite:** `skills/service-catalog-portfolio-deployer/evals/evals.json`
- **Legacy test cases:** `skills/service-catalog-portfolio-deployer/eval/test-cases.yaml`
