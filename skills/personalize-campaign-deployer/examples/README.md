# End-to-End Example: Personalize Campaign Deployment

A walkthrough showing how to use the `personalize-campaign-deployer`
skill from invocation through verification. Mirrors the structured-
eval pattern of shipping a concrete worked example per skill.

---

## Scenario

You are deploying a CUSTOM Personalize recommendation pipeline with
the User-Personalization recipe, HPO training, a campaign at
minProvisionedTPS=1 (dev), and an event tracker for real-time updates.
The pipeline needs:

- Dataset group: retail-recs (CUSTOM)
- Interactions data: s3://training-data/interactions.csv
- Schema: USER_ID, ITEM_ID, TIMESTAMP, EVENT_TYPE
- Recipe: aws-user-personalization
- Training: HPO enabled
- Campaign: minProvisionedTPS=1
- Event tracker: enabled
- Region: us-east-1
- Account: 123456789012

---

## Step 1 — Invoke the skill

### Option A: Slash command

```
/aws:deploy-personalize-campaign
```

Then paste the requirements.

### Option B: Natural language

```
You: "Build a Personalize recommendation system for a retail site.
      CUSTOM dataset group. User-Personalization recipe with HPO.
      Campaign minProvisionedTPS=1. Enable event tracker."
```

### Option C: CLI routing

```bash
node cli/bin/cli.js route "deploy personalize recommendation pipeline"
```

---

## Step 2 — Skill produces the READY_TO_DEPLOY checklist

```text
PERSONALIZE_PIPELINE: retail-recs → aws-user-personalization → retail-campaign
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓] Dataset group: retail-recs (CUSTOM) — arn:aws:personalize:us-east-1:123456789012:dataset-group/retail
  [✓] Interactions dataset: schema interactions-schema (4 fields)
  [✓] Bulk import: s3://training-data/interactions.csv → interactions (ACTIVE)
  [✓] Recipe: aws-user-personalization (CUSTOM)
  [✓] Solution version: HPO
  [✓] Campaign: retail-campaign — minProvisionedTPS=1
  [✓] Event tracker: retail-event-tracker — tracking-id abc-track
  [✓] IAM — s3:GetObject: PersonalizeS3ReadRole
  [✓] IAM — personalize:*: PersonalizeServiceRole
VERIFICATION_COMMANDS:
  aws personalize describe-campaign --campaign-arn arn:aws:personalize:us-east-1:123456789012:campaign/retail --region us-east-1
  aws personalize-runtime get-recommendations --campaign-arn arn:...:campaign/retail --user-id user-123 --region us-east-1
```

---

## Step 3 — Provisioning commands

```bash
# Step 1: Create dataset group
DSG_ARN=$(aws personalize create-dataset-group \
  --name retail-recs --domain CUSTOM --region us-east-1 \
  --query 'datasetGroupArn' --output text)

# Step 2: Create schema and dataset
SCHEMA_ARN=$(aws personalize create-schema \
  --name interactions-schema \
  --schema file://interactions-schema.json \
  --region us-east-1 --query 'schemaArn' --output text)

DS_ARN=$(aws personalize create-dataset \
  --name interactions --dataset-group-arn "$DSG_ARN" \
  --dataset-type INTERACTIONS --schema-arn "$SCHEMA_ARN" \
  --region us-east-1 --query 'datasetArn' --output text)

# Step 3: Bulk import
IMPORT_ARN=$(aws personalize create-dataset-import-job \
  --job-name interactions-import-001 \
  --dataset-arn "$DS_ARN" \
  --data-source '{"dataLocation":"s3://training-data/interactions.csv"}' \
  --role-arn arn:aws:iam::123456789012:role/PersonalizeS3ReadRole \
  --region us-east-1 --query 'datasetImportJobArn' --output text)

# Wait for ACTIVE: aws personalize describe-dataset-import-job --dataset-import-job-arn "$IMPORT_ARN"

# Step 4: Create solution with User-Personalization
SOL_ARN=$(aws personalize create-solution \
  --name user-personalization-solution \
  --dataset-group-arn "$DSG_ARN" \
  --recipe-arn arn:aws:personalize:::recipe/aws-user-personalization \
  --region us-east-1 --query 'solutionArn' --output text)

# Step 5: Train solution version with HPO
SV_ARN=$(aws personalize create-solution-version \
  --solution-arn "$SOL_ARN" --training-mode FULL --perform-hpo \
  --region us-east-1 --query 'solutionVersionArn' --output text)

# Wait for ACTIVE: aws personalize describe-solution-version --solution-version-arn "$SV_ARN"

# Step 6: Create campaign (minProvisionedTPS=1 — cost floor)
CAMP_ARN=$(aws personalize create-campaign \
  --name retail-campaign \
  --solution-version-arn "$SV_ARN" \
  --min-provisioned-tps 1 \
  --region us-east-1 --query 'campaignArn' --output text)

# Step 7: Create event tracker
TRACKING_ID=$(aws personalize create-event-tracker \
  --name retail-event-tracker --dataset-group-arn "$DSG_ARN" \
  --region us-east-1 --query 'trackingId' --output text)

echo "Campaign: $CAMP_ARN"
echo "Tracking ID: $TRACKING_ID"
```

---

## Step 4 — Post-deployment verification

```bash
# Campaign status — should be ACTIVE
aws personalize describe-campaign \
  --campaign-arn "$CAMP_ARN" \
  --query 'campaign.status' --region us-east-1

# Test recommendations
aws personalize-runtime get-recommendations \
  --campaign-arn "$CAMP_ARN" \
  --user-id user-001 \
  --num-results 10 \
  --region us-east-1

# Solution metrics
aws personalize get-solution-metrics \
  --solution-version-arn "$SV_ARN" \
  --region us-east-1
```

---

## What the skill catches that a naive deployment misses

| Configuration | Naive deployment | Skill output | Why the skill is right |
|---|---|---|---|
| Recipe | SIMS or Popularity-Counting (wrong default) | User-Personalization (aws-user-personalization) | Covers ~90% of cases; handles cold-start + event tracker |
| minProvisionedTPS | High default (e.g., 10) | 1 for dev; tune for prod | Sets cost floor; billed 24/7 |
| Event tracker | Forgotten | Created with tracking-id | Enables real-time updates without retraining |
| Schema immutability | Tries to edit columns later | Immutable — plan columns upfront | Schema cannot be edited after creation |
| Training mode | Manual (no HPO) | HPO for better metrics | HPO explores hyperparameter space |
| Interactions required | Provides Users only | Verifies Interactions is present | Interactions is the REQUIRED minimum dataset |
| DOMAIN vs CUSTOM | CUSTOM for e-commerce | Recommenders for ECOMMERCE/VIDEO/MUSIC | DOMAIN groups use pre-built recipes |

---

## Related artifacts

- **Skill definition:** `skills/personalize-campaign-deployer/SKILL.md`
- **Datasets + recipes guide:** `skills/personalize-campaign-deployer/references/datasets-and-recipes.md`
- **Campaigns + events guide:** `skills/personalize-campaign-deployer/references/campaigns-and-events.md`
- **Slash command:** `commands/aws/deploy-personalize-campaign.md`
- **Eval suite:** `skills/personalize-campaign-deployer/evals/evals.json`
- **Legacy test cases:** `skills/personalize-campaign-deployer/eval/test-cases.yaml`
