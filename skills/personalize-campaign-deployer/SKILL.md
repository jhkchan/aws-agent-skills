---
name: personalize-campaign-deployer
description: 'Deploys Amazon Personalize recommendation pipelines with production defaults: dataset group creation (CUSTOM or DOMAIN), dataset types (Interactions, Users, Items), Avro-like JSON schema, bulk import from S3 and incremental events via PutEvents, solution creation with recipe selection (User-Personalization, SIMS, Popularity- Counting), solution version training (HPO vs manual), campaign creation with minProvisionedTPS, event tracker for real-time updates, batch inference jobs, recommender creation for DOMAIN groups, filter creation, campaign offline metrics, and AutoTraining. Emits a READY_TO_DEPLOY checklist with verification commands. Use when building a recommendation system, training a Personalize solution. Triggers: create personalize dataset group, personalize schema, personalize solution, personalize recipe, personalize campaign, personalize minProvisionedTPS, personalize event tracker, personalize put events, personalize batch inference, personalize recommender, personalize filter, personalize HPO.'
license: Apache-2.0
compatibility: 'Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). For live deployment: AWS CLI v2 with personalize access and an IAM role granting s3:GetObject on the training-data bucket, iam:PassRole for the Personalize service role, and personalize:* actions. Works with Lambda runtimes (boto3 personalize-runtime client for GetRecommendations and PutEvents), Terraform aws_personalize_* resources, and CloudFormation AWS::Personalize::* templates.'
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: 'true'
  phase: '1'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: AI/ML
  task_type: deploy
  skill_class: capability
  lifecycle_status: active
  verdict_shape: READY_TO_DEPLOY | PREREQUISITES_MISSING
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  tags: aws, personalize, recommendations, ml, deploy, provisioning, dataset-group, recipe, campaign, event-tracker, batch-inference
  dependencies: aws-orchestrator
  keywords: aws, personalize, recommendations, recommendation system, dataset group, interactions, users, items, schema, recipe, user-personalization, sims, popularity-counting, solution, campaign, minprovisionedtps, event tracker, put events, batch inference, recommender, filter, hpo, ml, deploy, provisioning
  when_to_use: Invoke when the user wants to build a recommendation system using Amazon Personalize. Covers dataset group creation (CUSTOM or DOMAIN), dataset schema definition (Avro-like JSON for Interactions, Users, Items), bulk data import from S3, incremental events via PutEvents, solution creation with recipe selection (User-Personalization, SIMS, Popularity-Counting), solution version training with HPO, campaign creation with minProvisionedTPS, event tracker for real-time recommendations, batch inference jobs, recommender creation for DOMAIN dataset groups, filter creation, and campaign metrics. Do NOT invoke for Amazon SageMaker custom models, Amazon Bedrock, or Amazon OpenSearch recommendations.
---

# Personalize Campaign Deployer

An AWS CloudOps agent skill that deploys Amazon Personalize
recommendation pipelines with correct defaults. The skill walks the
operator through dataset group creation, schema definition, data
import, recipe selection, solution training, campaign creation with
minProvisionedTPS, event tracker for real-time updates, batch
inference, recommender creation for DOMAIN groups, filter creation,
and campaign metrics, captures the recommendation topology, explains
why each default matters, and emits a READY_TO_DEPLOY checklist with
copy-pasteable verification commands.

## Activation keywords

create personalize dataset group, personalize schema, personalize
data import, personalize solution, personalize recipe, personalize
campaign, personalize minProvisionedTPS, personalize event tracker,
personalize put events, personalize batch inference, personalize
recommender, personalize filter, personalize HPO.

## STRICT output contract

When this skill is invoked with a Personalize-deployment request
(build a recommendation system, create a dataset group, train a
solution, deploy a campaign, set up an event tracker, run batch
inference, or a partial configuration), the agent MUST respond with
the READY_TO_DEPLOY checklist defined in the "Output format" section
using the literal all-caps labels `PERSONALIZE_PIPELINE:`, `VERDICT:`,
`CHECKLIST:`, and `VERIFICATION_COMMANDS:`. Do NOT preface the
checklist with prose, headings, or disclaimers — emit the block as the
first lines of the response. This contract is what assertion-based
evals and downstream provisioning pipelines rely on; deviating from
the literal labels breaks automation silently.

If any prerequisite is missing, the verdict is `PREREQUISITES_MISSING`
with a specific gap citation in the checklist (marked `[✗]`), and
`READY_TO_DEPLOY` MUST NOT also appear.

## Quick navigation

| Section | When to read |
|---|---|
| Prerequisites | Always — verify before provisioning |
| Step 1 — Dataset group (CUSTOM vs DOMAIN) | Topology choice |
| Step 2 — Datasets and schema (Avro-like JSON) | Data model |
| Step 3 — Bulk data import from S3 | Training data |
| Step 4 — Recipe selection | Algorithm choice |
| Step 5 — Solution and solution version (HPO) | Training |
| Step 6 — Campaign creation (minProvisionedTPS) | Serving |
| Step 7 — Event tracker (PutEvents real-time) | Real-time updates |
| Step 8 — Batch inference jobs | Offline scoring |
| Step 9 — Recommenders (DOMAIN groups) | Domain-optimized |
| Step 10 — Filters | Recommendation filtering |
| Step 11 — Campaign metrics and update | Evaluation |
| Step 12 — Recent features | Latest |
| NEVER do these things | Review before signing off |
| Output format | The literal checklist template |
| references/datasets-and-recipes.md | Dataset + recipe detail |
| references/campaigns-and-events.md | Campaign + event tracker detail |

## Prerequisites (verify before provisioning)

Before emitting provisioning commands, verify these prerequisites. If
any are missing, the verdict is **PREREQUISITES_MISSING**.

| Prerequisite | Why it matters | How to verify |
|---|---|---|
| S3 training-data bucket exists (same region) | Bulk import reads CSV from S3 | `aws s3api head-bucket --bucket <bucket>` |
| Training CSV headers match schema | Mismatch causes import failure | Validate against schema |
| IAM: s3:GetObject on S3 + iam:PassRole | Personalize reads training data and assumes role | Review role policy |
| IAM: personalize:* actions | Required for dataset group, solution, campaign | Review IAM policy |
| Interactions dataset defined | Interactions is the REQUIRED minimum dataset | Schema has USER_ID, ITEM_ID, TIMESTAMP, EVENT_TYPE |
| At least 1000 interactions | Minimum data volume for training (recommended) | Count rows in CSV |
| Dataset group type decided (CUSTOM vs DOMAIN) | Determines solutions+campaigns vs recommenders | ECOMMERCE/VIDEO/MUSIC or CUSTOM |
| Recipe selected (CUSTOM groups) | Determines algorithm | aws-user-personalization for most cases |
| minProvisionedTPS decided | Sets cost floor | Start at 1 for dev; tune for prod |

If any prerequisite is missing, output `VERDICT: PREREQUISITES_MISSING`
and cite the specific gap.

## Step 1 — Dataset group (CUSTOM vs DOMAIN)

Create a dataset group first. The type determines the downstream flow.

```bash
# CUSTOM (full control — solutions + campaigns)
aws personalize create-dataset-group --name retail-recs --domain CUSTOM --region us-east-1

# DOMAIN (pre-built recommenders — ECOMMERCE / VIDEO / MUSIC)
aws personalize create-dataset-group --name ecommerce-recs --domain ECOMMERCE --region us-east-1
```

Available domains: `ECOMMERCE`, `VIDEO`, `MUSIC`. DOMAIN groups use
pre-built recommenders instead of custom solutions + campaigns.

## Step 2 — Datasets and schema (Avro-like JSON)

Personalize uses three dataset types: Interactions (required), Users
(optional), Items (optional). Each dataset has an Avro-like JSON
schema. The minimum Interactions schema requires USER_ID (string),
ITEM_ID (string), TIMESTAMP (long), and EVENT_TYPE (string). Common
optional fields include EVENT_VALUE, IMPRESSION, RESERVATION.

```json
{
  "type": "record",
  "name": "Interactions",
  "namespace": "com.amazonaws.personalize.schema",
  "fields": [
    {"name": "USER_ID", "type": "string"},
    {"name": "ITEM_ID", "type": "string"},
    {"name": "TIMESTAMP", "type": "long"},
    {"name": "EVENT_TYPE", "type": "string"}
  ],
  "version": "1.0"
}
```

Create the schema (`create-schema`), then create the dataset
referencing the schema (`create-dataset --dataset-type INTERACTIONS`).
Full CLI for both is in `references/datasets-and-recipes.md`.

**Critical:** the schema is IMMUTABLE after creation. To add columns,
create a new schema and dataset, then re-import data.

## Step 3 — Bulk data import from S3

Import training data from S3. The CSV must have headers matching the
schema columns. The service role must trust `personalize.amazonaws.com`
and grant `s3:GetObject` + `s3:ListBucket` on the training-data bucket
(full trust + permission JSON is in `references/datasets-and-recipes.md`).

```bash
aws personalize create-dataset-import-job \
  --job-name interactions-import-001 \
  --dataset-arn <dataset-arn> \
  --data-source '{"dataLocation":"s3://my-training-data/interactions.csv"}' \
  --role-arn arn:aws:iam::123456789012:role/PersonalizeS3ReadRole \
  --region us-east-1
```

Wait for the import job to reach ACTIVE status before creating a
solution. For incremental updates, use PutEvents (via event tracker)
or another import job.

## Step 4 — Recipe selection (CUSTOM groups)

For CUSTOM dataset groups, choose a recipe. The recipe ARN format is
`arn:aws:personalize:::recipe/aws-<recipe-name>`. See the
"Expert heuristic: recipe selection" section above for the full
matrix. **Default: `aws-user-personalization`** unless you have a
specific reason — it handles cold-start, supports event tracker, and
produces personalized results.

## Step 5 — Solution and solution version (HPO vs manual)

A solution binds a recipe to a dataset group. A solution version is a
trained model instance.

**Create the solution:**

```bash
aws personalize create-solution \
  --name user-personalization-solution \
  --dataset-group-arn <dataset-group-arn> \
  --recipe-arn arn:aws:personalize:::recipe/aws-user-personalization \
  --region us-east-1
```

**Create the solution version (HPO enabled):**

```bash
aws personalize create-solution-version \
  --solution-arn <solution-arn> \
  --training-mode FULL \
  --perform-hpo \
  --region us-east-1
```

`--perform-hpo` enables hyperparameter optimization (longer training,
potentially better metrics). Without it, Personalize uses the recipe's
default hyperparameters. `--training-mode FULL` retrains from scratch;
`UPDATE` updates incrementally.

**Training time:** typically 30 minutes to several hours, depending on
data volume and HPO. Wait for status ACTIVE before creating a campaign.

## Step 6 — Campaign creation (minProvisionedTPS)

A campaign serves real-time recommendations from a solution version.

```bash
aws personalize create-campaign \
  --name retail-campaign \
  --solution-version-arn <solution-version-arn> \
  --min-provisioned-tps 1 \
  --campaign-config '{"itemExplorationConfig":{"coldItemRelativeWeight":0.1,"enableMetadataWithRecommendations":true}}' \
  --region us-east-1

# Update minProvisionedTPS without recreating
aws personalize update-campaign \
  --campaign-arn <campaign-arn> \
  --min-provisioned-tps 5 --region us-east-1

# GetRecommendations (real-time serving)
aws personalize-runtime get-recommendations \
  --campaign-arn <campaign-arn> --user-id user-123 --num-results 10 --region us-east-1
```

**minProvisionedTPS sets the cost floor.** Start at 1 for dev/staging;
set to your median TPS for production.

## Step 7 — Event tracker (PutEvents real-time updates)

An event tracker enables real-time recommendation updates without full
retraining. Create the tracker; the returned `tracking-id` is used in
PutEvents calls.

```bash
aws personalize create-event-tracker \
  --name retail-event-tracker \
  --dataset-group-arn <dataset-group-arn> \
  --region us-east-1
```

**PutEvents (Python SDK):**

```python
import boto3
personalize_events = boto3.client("personalize-events")

personalize_events.put_events(
    trackingId="abc123-tracking-id",
    userId="user-123",
    sessionId="session-456",
    eventList=[{
        "eventId": "event-001",
        "eventType": "click",
        "itemId": "item-789",
        "sentAt": 1722816000,
        "properties": '{"eventValue": 1.0}'
    }]
)
```

**Critical:** only ONE active event tracker per dataset group.
Recreating the tracker invalidates the previous tracking ID. Full
PutEvents integration patterns are in
`references/campaigns-and-events.md`.

## Step 8 — Batch inference jobs

For offline scoring (e.g., nightly recommendation refresh for a user
list), use a batch inference job.

```bash
aws personalize create-batch-inference-job \
  --job-name nightly-recommendations-2026-08-05 \
  --solution-version-arn <solution-version-arn> \
  --job-input '{"s3DataSource":{"path":"s3://my-input/users.json"}}' \
  --job-output '{"s3DataDestination":{"path":"s3://my-output/recommendations/"}}' \
  --role-arn arn:aws:iam::123456789012:role/PersonalizeBatchRole \
  --num-results 25 \
  --region us-east-1
```

Input is JSON Lines (`{"userId": "user-123"}`); output is per-user
recommendation JSON written to the S3 path.

## Step 9 — Recommenders (DOMAIN dataset groups)

For DOMAIN (ECOMMERCE, VIDEO, MUSIC) groups, use recommenders instead
of solutions + campaigns. Each domain has pre-built recipes.

```bash
aws personalize create-recommender \
  --name recommended-for-you \
  --dataset-group-arn <ecommerce-dataset-group-arn> \
  --recipe-arn arn:aws:personalize:::recipe/aws-ecomm-recommended-for-you \
  --recommender-config '{"minRecommendationRequestsPerSecond": 1}' \
  --region us-east-1
```

**ECOMMERCE recommenders:** Recommended For You, Users Who Viewed X
Also Viewed, Frequently Bought Together, Popular Items, Most
Purchased. **VIDEO:** Recommended For You, Because You Watched, Top
Picks, Continue Watching. **MUSIC:** similar pre-built recipes. Call
GetRecommendations with the recommender ARN instead of a campaign ARN.
`minRecommendationRequestsPerSecond` is the DOMAIN equivalent of
minProvisionedTPS — it sets the cost floor.

## Step 10 — Filters

Filters restrict recommendations (e.g., exclude out-of-stock items,
include only a category).

```bash
aws personalize create-filter \
  --name exclude-out-of-stock \
  --dataset-group-arn <dataset-group-arn> \
  --filter-expression 'EXCLUDE ItemID WHERE Items.IN_STOCK IN ("false")' \
  --region us-east-1
```

Apply the filter at GetRecommendations time:

```bash
aws personalize-runtime get-recommendations \
  --campaign-arn <campaign-arn> \
  --user-id user-123 \
  --filter-arn <filter-arn> \
  --region us-east-1
```

Filter expressions reference dataset columns. Validate the expression
syntax in the Personalize docs before creating.

## Step 11 — Campaign metrics and update

Each solution version has offline metrics (computed during training)
that indicate recommendation quality.

```bash
aws personalize get-solution-metrics \
  --solution-version-arn <solution-version-arn> --region us-east-1
# Returns: coverage, mean_reciprocal_rank, normalized_discounted_cumulative_gain,
# precision_at_k, recall_at_k. Higher is better.

# Update campaign to a new solution version (~15 min; UPDATE_PENDING)
aws personalize update-campaign \
  --campaign-arn <campaign-arn> \
  --solution-version-arn <new-solution-version-arn> --region us-east-1

# AutoTraining (2023+): automatic retraining on a schedule
aws personalize update-solution \
  --solution-arn <solution-arn> --perform-auto-training \
  --solution-update-config '{"autoTrainingConfig":{"schedulingExpression":"rate(7 days)"}}' \
  --region us-east-1
```

## Step 12 — Recent features

> Moved to [references/advanced-patterns.md](references/advanced-patterns.md#step-12--recent-features).
> AutoTraining GA, MUSIC domain recommenders, trending recipes, dataset limits, cold-start, filter operators, regions, PutEvents throughput.

## NEVER do these things

1. **NEVER set a high minProvisionedTPS without justification.** It
   sets the cost floor, billed 24/7. Start at 1 for dev; tune up for
   production based on observed traffic.

2. **NEVER use Popularity-Counting as your production recipe.** It is
   a baseline. Use User-Personalization (aws-user-personalization)
   for personalized recommendations — it covers ~90% of use cases.

3. **NEVER assume the schema can be edited after creation.** Personalize
   schemas are IMMUTABLE. To add columns, create a new schema + dataset
   and re-import data.

4. **NEVER create an event tracker without planning for its tracking
   ID.** Only ONE active event tracker per dataset group. Recreating
   invalidates the previous tracking ID and breaks any client using it.

5. **NEVER use SIMS for personalized user recommendations.** SIMS
   (aws-sims) is for item-to-item similarity. For user recommendations,
   use User-Personalization.

6. **NEVER forget to wait for solution-version ACTIVE before creating
   a campaign.** Creating a campaign against a CREATE-PENDING or
   CREATE-FAILED solution version fails.

7. **NEVER skip the bulk import job status check.** Wait for the
   import job to reach ACTIVE before creating a solution. Training
   against partially-imported data produces poor recommendations.

8. **NEVER assume recommendations update in real-time without an
   event tracker.** Without PutEvents feeding the event tracker,
   recommendations are frozen at training time. Enable an event tracker
   for any production system.

9. **NEVER mix DOMAIN and CUSTOM flows.** DOMAIN groups use
   recommenders; CUSTOM groups use solutions + campaigns. The two are
   not interchangeable within a single dataset group.

10. **NEVER ignore offline metrics.** `precision_at_k`,
    `normalized_discounted_cumulative_gain`, and `mean_reciprocal_rank`
    indicate recommendation quality. If metrics are low after training,
    check data volume, EVENT_TYPE distribution, and recipe choice.

## Output format

```text
PERSONALIZE_PIPELINE: <dataset-group-name> → <recipe-or-recommender> → <campaign-or-recommender>
VERDICT: READY_TO_DEPLOY | PREREQUISITES_MISSING
CHECKLIST:
  [✓|✗] Dataset group: <name> (<CUSTOM|ECOMMERCE|VIDEO|MUSIC>) — <arn>
  [✓|✗] Interactions dataset: schema <name> (<n> fields) — <arn>
  [✓|✗] Users dataset: schema <name> (<n> fields) — <arn> | Not used
  [✓|✗] Items dataset: schema <name> (<n> fields) — <arn> | Not used
  [✓|✗] Bulk import: s3://<bucket>/<key> → <dataset> (<status>)
  [✓|✗] Recipe: aws-<recipe-name> (CUSTOM) | <recommender-recipe> (DOMAIN)
  [✓|✗] Solution: <name> — <arn>
  [✓|✗] Solution version: <arn> (<status>) [HPO|manual]
  [✓|✗] Campaign: <name> — minProvisionedTPS=<tps> — <arn>
  [✓|✗] Event tracker: <name> — tracking-id <id> | Not used
  [✓|✗] Filter: <name> (<expression>) — <arn> | Not used
  [✓|✗] Batch inference: <job-name> → s3://<output> | Not used
  [✓|✗] Metrics: precision_at_k=<val>, NDCG=<val>, MRR=<val>
  [✓|✗] AutoTraining: <schedule> | Disabled
  [✓|✗] IAM — s3:GetObject: <role>
  [✓|✗] IAM — personalize:*: <role>
VERIFICATION_COMMANDS:
  aws personalize describe-campaign --campaign-arn <arn> --region <region>
  aws personalize describe-solution-version --solution-version-arn <arn> --region <region>
  aws personalize-runtime get-recommendations --campaign-arn <arn> --user-id <id> --region <region>
```

### Worked example — CUSTOM User-Personalization campaign with event tracker

```text
PERSONALIZE_PIPELINE: retail-recommendations → aws-user-personalization → retail-campaign
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓] Dataset group: retail-recommendations (CUSTOM) — arn:aws:personalize:us-east-1:123456789012:dataset-group/retail
  [✓] Interactions dataset: schema interactions-schema (4 fields)
  [✓] Bulk import: s3://my-training-data/interactions.csv → interactions (ACTIVE)
  [✓] Recipe: aws-user-personalization (CUSTOM)
  [✓] Solution version: arn:...:solution-version/abc123 (ACTIVE) [HPO]
  [✓] Campaign: retail-campaign — minProvisionedTPS=1
  [✓] Event tracker: retail-event-tracker — tracking-id abc-track
  [✓] IAM — s3:GetObject: PersonalizeS3ReadRole
  [✓] IAM — personalize:*: PersonalizeServiceRole
VERIFICATION_COMMANDS:
  aws personalize describe-campaign --campaign-arn arn:aws:personalize:us-east-1:123456789012:campaign/retail --region us-east-1
  aws personalize-runtime get-recommendations --campaign-arn arn:...:campaign/retail --user-id user-123 --region us-east-1
```

## References (load on demand)

- [advanced-patterns](references/advanced-patterns.md) — mindset, configuration dependency graph, recent features (2023-2026)
- [error-handling](references/error-handling.md) — CREATE_FAILED, CREATE_PENDING, import, PutEvents, filter, UPDATE_PENDING, high-bill fixes
- [datasets-and-recipes](references/datasets-and-recipes.md) — dataset + recipe detail, CUSTOM vs DOMAIN and recipe-selection heuristics 
- [campaigns-and-events](references/campaigns-and-events.md) — campaign + event tracker detail, minProvisionedTPS cost-floor and event-tracker heuristics

## Domain

AWS CloudOps / Amazon Personalize Recommendation System Provisioning.

## AWS documentation

- **Personalize Developer Guide** — https://docs.aws.amazon.com/personalize/latest/dg/
- **Dataset groups** — https://docs.aws.amazon.com/personalize/latest/dg/dataset-groups.html
- **Schemas and datasets** — https://docs.aws.amazon.com/personalize/latest/dg/data-prep-formatting.html
- **Recipes** — https://docs.aws.amazon.com/personalize/latest/dg/working-with-predefined-recipes.html
- **Campaigns** — https://docs.aws.amazon.com/personalize/latest/dg/campaigns.html
- **Event tracker** — https://docs.aws.amazon.com/personalize/latest/dg/recording-events.html
- **Batch inference jobs** — https://docs.aws.amazon.com/personalize/latest/dg/getting-batch-recommendations.html
- **Domain recommenders** — https://docs.aws.amazon.com/personalize/latest/dg/domain-recommenders.html
- **Filters** — https://docs.aws.amazon.com/personalize/latest/dg/filter.html
- **Pricing (minProvisionedTPS)** — https://aws.amazon.com/personalize/pricing/
