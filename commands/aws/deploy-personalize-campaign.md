---
description: Deploy an Amazon Personalize recommendation pipeline with production-grade defaults (CUSTOM vs DOMAIN dataset group, Interactions/Users/Items schemas, bulk import from S3, recipe selection — User-Personalization, SIMS, Popularity-Counting, solution version with HPO, campaign with minProvisionedTPS, event tracker for real-time PutEvents, batch inference jobs, recommenders for DOMAIN groups, filters, and solution metrics). Emits a READY_TO_DEPLOY checklist with verification commands.
nl_triggers:
  - "create personalize dataset group"
  - "personalize schema"
  - "personalize data import"
  - "personalize solution"
  - "personalize recipe"
  - "personalize campaign"
  - "personalize minprovisionedtps"
  - "personalize event tracker"
  - "personalize put events"
  - "personalize batch inference"
  - "personalize recommender"
  - "personalize filter"
  - "personalize hpo"
  - "personalize pipeline"
  - "deploy personalize"
  - "recommendation system"
  - "user personalization"
routes_to: personalize-campaign-deployer
---

# /aws:deploy-personalize-campaign

Activate the `personalize-campaign-deployer` skill and deploy an
Amazon Personalize recommendation pipeline with production-grade
defaults.

## What it does

The skill walks the provisioning procedure and emits a
READY_TO_DEPLOY checklist:

1. Dataset group (CUSTOM vs DOMAIN: ECOMMERCE/VIDEO/MUSIC)
2. Datasets and schema (Avro-like JSON for Interactions/Users/Items)
3. Bulk data import from S3 (IAM service role)
4. Recipe selection (User-Personalization covers 90% of cases)
5. Solution and solution version (HPO vs manual, AutoTraining)
6. Campaign creation (minProvisionedTPS sets the cost floor)
7. Event tracker (PutEvents real-time updates)
8. Batch inference jobs (offline scoring from S3)
9. Recommenders (DOMAIN groups — pre-built recipes)
10. Filters (exclude/include expressions)
11. Solution metrics and campaign update
12. Recent features (AutoTraining, cold-start improvements)

## When to use

- You need to build a recommendation system.
- You are training a Personalize solution (User-Personalization, SIMS).
- You are creating a campaign with minProvisionedTPS.
- You want real-time recommendations via event tracker and PutEvents.
- You are running batch inference for offline scoring.
- You are deploying a DOMAIN recommender (ECOMMERCE/VIDEO/MUSIC).
- You need filters to exclude/include items in recommendations.
- You need to evaluate solution metrics (precision_at_k, NDCG).

## When NOT to use

- **Amazon SageMaker custom models** — use SageMaker skills for custom
  ML model training and deployment.
- **Amazon Bedrock** — different service for foundation models.
- **Amazon OpenSearch recommendations** — different pattern.
- **Auditing existing Personalize campaigns** — use Personalize audit
  skills.

## How to invoke

### Slash command

```
/aws:deploy-personalize-campaign
```

Then provide: dataset group type (CUSTOM / ECOMMERCE / VIDEO / MUSIC),
interactions S3 path, schema (or field list), recipe (or "recommended"
for the default), training mode (HPO / manual), campaign
minProvisionedTPS, event tracker (yes / no), filter expression (if
any), batch inference S3 paths (if any), region, role ARN, account.

### Natural language

Any of these routes to the same skill:

- "build a Personalize recommendation system for my retail site"
- "create a User-Personalization campaign with HPO"
- "deploy an event tracker for real-time recommendations"
- "set up a batch inference job for nightly user scoring"
- "create an ECOMMERCE recommender for my shop"

### CLI routing

```bash
node cli/bin/cli.js route "deploy personalize recommendation pipeline"
```

## Pipeline integration

This skill operates in **Phase 1 (Deploy)** of the CloudOps pipeline.
The orchestrator routes to it when the user wants to deploy Personalize
recommendation workloads. The output checklist feeds into verification
pipelines and downstream audit skills.

## Example

```
You: /aws:deploy-personalize-campaign

     Build a Personalize recommendation system for a retail site.
     CUSTOM dataset group. User-Personalization recipe with HPO.
     Campaign minProvisionedTPS=1. Enable event tracker.

Skill:
  PERSONALIZE_PIPELINE: retail-recs → aws-user-personalization → retail-campaign
  VERDICT: READY_TO_DEPLOY
  CHECKLIST:
    [✓] Dataset group: retail-recs (CUSTOM)
    [✓] Recipe: aws-user-personalization
    [✓] Solution version: HPO
    [✓] Campaign: retail-campaign — minProvisionedTPS=1
    [✓] Event tracker: enabled — tracking-id abc-track
  VERIFICATION_COMMANDS:
    aws personalize describe-campaign --campaign-arn <arn> --region us-east-1
    aws personalize-runtime get-recommendations --campaign-arn <arn> --user-id user-123 --region us-east-1
```

## References

- Skill definition: `skills/personalize-campaign-deployer/SKILL.md`
- Datasets + recipes guide: `skills/personalize-campaign-deployer/references/datasets-and-recipes.md`
- Campaigns + events guide: `skills/personalize-campaign-deployer/references/campaigns-and-events.md`
- Eval suite: `skills/personalize-campaign-deployer/evals/evals.json`
