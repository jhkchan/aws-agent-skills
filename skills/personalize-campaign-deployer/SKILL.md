---
name: personalize-campaign-deployer
description: >-
  Deploys Amazon Personalize recommendation pipelines with production
  defaults: dataset group creation (CUSTOM or DOMAIN), dataset types
  (Interactions, Users, Items), Avro-like JSON schema, bulk import
  from S3 and incremental events via PutEvents, solution creation
  with recipe selection (User-Personalization, SIMS, Popularity-
  Counting), solution version training (HPO vs manual), campaign
  creation with minProvisionedTPS, event tracker for real-time
  updates, batch inference jobs, recommender creation for DOMAIN
  groups, filter creation, campaign offline metrics, and AutoTraining.
  Emits a READY_TO_DEPLOY checklist with verification commands. Use
  when building a recommendation system, training a Personalize
  solution, creating a campaign, deploying real-time recommendations,
  configuring event tracker, running batch inference, or selecting a
  recipe. Triggers: create personalize dataset group, personalize
  schema, personalize solution, personalize recipe, personalize
  campaign, personalize minProvisionedTPS, personalize event tracker,
  personalize put events, personalize batch inference, personalize
  recommender, personalize filter, personalize HPO.
version: 0.1.0
author: Jacky Chan — AWS Community Builder
license: Apache-2.0
compatibility: >-
  Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf,
  Codex, Gemini). For live deployment: AWS CLI v2 with personalize
  access and an IAM role granting s3:GetObject on the training-data
  bucket, iam:PassRole for the Personalize service role, and
  personalize:* actions. Works with Lambda runtimes (boto3
  personalize-runtime client for GetRecommendations and PutEvents),
  Terraform aws_personalize_* resources, and CloudFormation
  AWS::Personalize::* templates.
keywords:
  - aws
  - personalize
  - recommendations
  - recommendation system
  - dataset group
  - interactions
  - users
  - items
  - schema
  - recipe
  - user-personalization
  - sims
  - popularity-counting
  - solution
  - campaign
  - minprovisionedtps
  - event tracker
  - put events
  - batch inference
  - recommender
  - filter
  - hpo
  - ml
  - deploy
  - provisioning
tags:
  - aws
  - personalize
  - recommendations
  - ml
  - deploy
  - provisioning
  - dataset-group
  - recipe
  - campaign
  - event-tracker
  - batch-inference
dependencies:
  - aws-orchestrator
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: true
  phase: 1
  supports_pipeline: true
  entry_point: false
  family: AI/ML
  task_type: deploy
  skill_class: capability
  lifecycle_status: active
  verdict_shape: "READY_TO_DEPLOY | PREREQUISITES_MISSING"
  version: 0.1.0
  author: "Jacky Chan — AWS Community Builder"
  tags:
    - aws
    - personalize
    - recommendations
    - ml
    - deploy
    - provisioning
    - dataset-group
    - recipe
    - campaign
    - event-tracker
    - batch-inference
  dependencies:
    - aws-orchestrator
  keywords:
    - create personalize dataset group
    - personalize schema
    - personalize data import
    - personalize solution
    - personalize recipe
    - personalize campaign
    - personalize minprovisionedtps
    - personalize event tracker
    - personalize put events
    - personalize batch inference
    - personalize recommender
    - personalize filter
    - personalize hpo
  when_to_use: >-
    Invoke when the user wants to build a recommendation system using
    Amazon Personalize. Covers dataset group creation (CUSTOM or DOMAIN),
    dataset schema definition (Avro-like JSON for Interactions, Users,
    Items), bulk data import from S3, incremental events via PutEvents,
    solution creation with recipe selection (User-Personalization, SIMS,
    Popularity-Counting), solution version training with HPO, campaign
    creation with minProvisionedTPS, event tracker for real-time
    recommendations, batch inference jobs, recommender creation for
    DOMAIN dataset groups, filter creation, and campaign metrics. Do NOT
    invoke for Amazon SageMaker custom models, Amazon Bedrock, or Amazon
    OpenSearch recommendations.
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

## Mindset

**One-line takeaway:** Amazon Personalize takes interaction data
(user-item interactions), trains a recommendation model (solution
version) using a recipe (User-Personalization, SIMS, Popularity-
Counting), and serves it via a campaign with a minProvisionedTPS
that sets the cost floor. The User-Personalization recipe covers
roughly 90% of recommendation use cases. An event tracker enables
real-time recommendation updates via PutEvents without retraining.

Three misconceptions dominate Personalize misdesign at provisioning
time:

- **"minProvisionedTPS is just a performance setting."** It is not.
  `minProvisionedTPS` sets the COST FLOOR for the campaign. Personalize
  bills per-TPS-hour; setting minProvisionedTPS=10 when you need 1
  means you pay for 10 TPS 24/7. Start low (1) and scale up based on
  observed traffic; you can update minProvisionedTPS without deleting
  the campaign.

- **"Use SIMS or Popularity-Counting by default."** Wrong default.
  The User-Personalization recipe (aws-user-personalization) covers
  ~90% of use cases — it handles cold-start, real-time updates via
  event tracker, and produces personalized (not just popular)
  recommendations. SIMS is for item-to-item similarity ("customers who
  bought X also bought Y"). Popularity-Counting is a baseline, not a
  production recommendation.

- **"Retraining is automatic."** It is not, unless you configure
  AutoTraining. By default, a solution version is trained once on the
  snapshot of data at training time. To incorporate new interactions,
  you must either retrain manually (create a new solution version and
  update the campaign), enable AutoTraining (automatic retraining on
  a schedule), or use the event tracker for real-time updates without
  full retraining.

## Configuration dependency graph (novel heuristic)

Personalize configurations are NOT independent. The dataset group type
determines whether you use campaigns or recommenders. The recipe
determines the solution. The solution version creates the campaign.
Use this graph to sequence provisioning.

| Configuration | Hard dependencies (API error without) | Silent failure / immutability | Enables downstream |
|---|---|---|---|
| Dataset group (CUSTOM or DOMAIN) | None (top-level) | DOMAIN groups use recommenders; CUSTOM uses solutions + campaigns | container for datasets |
| Dataset schema (Avro-like JSON) | Dataset group exists | IMMUTABLE after creation — cannot alter columns | typed columns for Interactions / Users / Items |
| Dataset (Interactions required) | Schema defined; dataset group exists | Interactions REQUIRED; Users/Items optional but recommended | the data store |
| Bulk import job | Dataset exists; S3 matches schema; IAM s3:GetObject | one-time; for updates use PutEvents or another import | trained model input |
| Solution (recipe) | Dataset group + Interactions dataset | recipe selection determines algorithm; cannot change after creation | algorithm blueprint |
| Solution version (training) | Solution exists; data imported | HPO takes longer but may improve metrics | trained model |
| Campaign | Solution version ACTIVE | minProvisionedTPS sets cost floor; can UPDATE without recreating | real-time GetRecommendations |
| Event tracker | Dataset group exists | ONE active tracker per group; recreating invalidates previous | real-time PutEvents updates |
| Filter | Dataset group exists | references dataset columns; validated at creation | filtered recommendations |
| Recommender (DOMAIN only) | DOMAIN dataset group exists | pre-built for ECOMMERCE / VIDEO / MUSIC | domain-optimized recs |
| Batch inference job | Solution version OR campaign exists; S3 I/O | writes JSON to S3; no real-time serving | offline scoring |

**The minProvisionedTPS row is the one a baseline model misses.** A
naive deployment sets minProvisionedTPS to a high default or does not
realize it sets the cost floor. The correct heuristic starts at 1 and
scales based on observed traffic. The procedure below forces an
explicit cost decision.

**Cross-dependency gotchas:**
- Schema is IMMUTABLE. To add columns, create a new schema + dataset
  and re-import.
- Event tracker is per dataset group. Only ONE active tracker per
  group; recreating invalidates the previous tracking ID.
- DOMAIN groups use recommenders; CUSTOM groups use the full solution
  → solution version → campaign flow. The two are not interchangeable.
- Campaign update (new solution version) takes effect within ~15
  minutes; the campaign is briefly in UPDATE_PENDING.

## Expert heuristic: choosing CUSTOM vs DOMAIN dataset groups

A baseline model says "create a dataset group." The correct heuristic
recognizes that the group type determines the entire downstream flow.

```text
Recommendation use case:
  ├── E-commerce (product recommendations)
  │     → DOMAIN (ECOMMERCE) — use pre-built recommenders
  │       Recommenders: Recommended For You, Users Who Viewed X Also Viewed,
  │                      Popular Items, Most Purchased, Frequently Bought Together
  │
  ├── Video / Media (content recommendations)
  │     → DOMAIN (VIDEO) — use pre-built recommenders
  │       Recommenders: Recommended For You, Because You Watched,
  │                      Top Picks, Continue Watching
  │
  ├── Music / Audio
  │     → DOMAIN (MUSIC) — use pre-built recommenders
  │
  └── Custom (non-standard domain, custom recipe)
        → CUSTOM — full control
          Solutions: User-Personalization, SIMS, Popularity-Counting,
                      Item-Attribute-Affinity, Personalized-Ranking
```

**Key implication:** if your use case fits ECOMMERCE, VIDEO, or MUSIC
domains, use a DOMAIN dataset group — it is faster to deploy and uses
AWS-optimized recipes. Use CUSTOM only when you need a non-standard
domain or custom recipe.

## Expert heuristic: recipe selection

Recipe selection is the core algorithmic decision for CUSTOM dataset
groups.

```text
Goal                                          → Recipe
────────────────────────────────────────────────────────────────────────────
Personalized recommendations (90% of cases)   → aws-user-personalization
  Handles cold-start, real-time events, HRNN
"Customers who viewed X also viewed Y"         → aws-sims
  Item-to-item similarity
Baseline / most-popular fallback               → aws-popularity-counting
Re-ranking a candidate list                    → aws-personalized-ranking
Item affinity by attribute                     → aws-item-attribute-affinity
```

**The User-Personalization recipe (aws-user-personalization) covers
~90% of use cases.** It combines HRNN (hierarchical recurrent neural
network), handles cold-start items and users, supports real-time
updates via event tracker, and produces personalized (not just
popular) recommendations. Start here unless you have a specific
reason to use another recipe.

## Expert heuristic: minProvisionedTPS sets the cost floor

`minProvisionedTPS` is the most impactful cost lever in Personalize.
It sets the minimum throughput (transactions per second) the campaign
will bill, 24/7, regardless of actual traffic.

```text
Cost math (illustrative, us-east-1):
  minProvisionedTPS = 1  → ~$0.20/hour → ~$150/month
  minProvisionedTPS = 5  → ~$1.00/hour → ~$730/month
  minProvisionedTPS = 10 → ~$2.00/hour → ~$1460/month
  minProvisionedTPS = 50 → ~$10.00/hour → ~$7300/month

Strategy:
  1. Start at minProvisionedTPS = 1 for dev/staging
  2. For production, set to your p50 TPS (median load)
  3. Auto-scaling handles spikes above minProvisionedTPS (billed per-transaction)
  4. Update minProvisionedTPS via update-campaign (no deletion required)
```

**Key implication:** never set a high minProvisionedTPS without
justification. The campaign auto-scales above the floor; you only pay
the floor for idle capacity. Start low and tune up.

## Expert heuristic: event tracker enables real-time updates

Without an event tracker, recommendations are frozen at training
time. With an event tracker, PutEvents feeds real-time interactions
into the campaign, updating recommendations without full retraining.

```text
Real-time update flow:
  User clicks an item
    → Lambda or SDK calls personalize-events:PutEvents
      → Event tracker writes to the dataset group
        → Campaign blends real-time signal with trained model
          → Next GetRecommendations reflects the recent click
```

**Key implication:** for any production recommendation system, an
event tracker is essential. Without it, recommendations are static
until the next full retraining. With it, the campaign adapts to user
behavior in near-real-time.

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

Create a dataset group first. The type (CUSTOM or DOMAIN) determines
the downstream flow.

**CUSTOM dataset group (full control):**

```bash
aws personalize create-dataset-group \
  --name retail-recommendations \
  --domain CUSTOM \
  --region us-east-1
```

**DOMAIN dataset group (ECOMMERCE example):**

```bash
aws personalize create-dataset-group \
  --name ecommerce-recommendations \
  --domain ECOMMERCE \
  --region us-east-1
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
`arn:aws:personalize:::recipe/aws-<recipe-name>`.

| Recipe | Use case | Real-time events |
|---|---|---|
| aws-user-personalization | Personalized recs (90% of cases) | Yes (event tracker) |
| aws-sims | Item-to-item similarity | No |
| aws-popularity-counting | Most-popular baseline | No |
| aws-personalized-ranking | Re-rank a candidate list | Yes |
| aws-item-attribute-affinity | Item affinity by attribute | No |

**Default recommendation:** use `aws-user-personalization` unless you
have a specific reason. It handles cold-start, supports event tracker,
and produces personalized results.

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
```

**minProvisionedTPS sets the cost floor.** Start at 1 for dev/staging.
For production, set to your median TPS. Update without recreating:

```bash
aws personalize update-campaign \
  --campaign-arn <campaign-arn> \
  --solution-version-arn <new-solution-version-arn> \
  --min-provisioned-tps 5 \
  --region us-east-1
```

**GetRecommendations (real-time serving):**

```bash
aws personalize-runtime get-recommendations \
  --campaign-arn <campaign-arn> \
  --user-id user-123 \
  --num-results 10 \
  --region us-east-1
```

## Step 7 — Event tracker (PutEvents real-time updates)

An event tracker enables real-time recommendation updates without full
retraining.

```bash
aws personalize create-event-tracker \
  --name retail-event-tracker \
  --dataset-group-arn <dataset-group-arn> \
  --region us-east-1
```

The returned `tracking-id` is used in PutEvents calls from your
application or Lambda.

**PutEvents (Python SDK):**

```python
import boto3

personalize_events = boto3.client("personalize-events")

personalize_events.put_events(
    trackingId="abc123-tracking-id",
    userId="user-123",
    sessionId="session-456",
    eventList=[
        {
            "eventId": "event-001",
            "eventType": "click",
            "itemId": "item-789",
            "sentAt": 1722816000,
            "properties": '{"eventValue": 1.0}'
        }
    ]
)
```

**Critical:** only ONE active event tracker per dataset group.
Recreating the tracker invalidates the previous tracking ID.

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

**Get solution metrics:**

```bash
aws personalize get-solution-metrics \
  --solution-version-arn <solution-version-arn> \
  --region us-east-1
```

Returns: `coverage`, `mean_reciprocal_rank`, `normalized_discounted_cumulative_gain`,
`precision_at_k`, `recall_at_k`. Higher is better for all.

**Update campaign (new solution version):**

```bash
aws personalize update-campaign \
  --campaign-arn <campaign-arn> \
  --solution-version-arn <new-solution-version-arn> \
  --region us-east-1
```

Update takes ~15 minutes; the campaign is briefly in UPDATE_PENDING.

**AutoTraining (2023+):** enable automatic retraining on a schedule.

```bash
aws personalize update-solution \
  --solution-arn <solution-arn> \
  --perform-auto-training \
  --solution-update-config '{"autoTrainingConfig":{"schedulingExpression":"rate(7 days)"}}' \
  --region us-east-1
```

## Step 12 — Recent features

**Recent AWS features (2023-2026):**

- **AutoTraining GA (2023-2024):** Automatic retraining on a schedule
  (e.g., every 7 days). Eliminates manual solution-version creation
  for routine refreshes.

- **Domain recommenders expanded (2023-2024):** MUSIC domain added;
  ECOMMERCE and VIDEO recommenders enhanced with cold-start handling.

- **Trending recipes (2023-2024):** New recipes for trending items
  and time-decay popularity.

- **Increased dataset limits (2024-2025):** Maximum interactions per
  dataset raised; larger bulk import jobs supported.

- **Cold-start improvements (2024-2025):** User-Personalization recipe
  enhanced for better cold-start user and item handling.

- **Filter improvements (2024-2025):** Filter expressions support
  additional operators and contextual filtering.

- **Regional expansion (2024-2025):** Personalize available in
  additional regions (ap-southeast-3, eu-south-1).

- **Real-time event throughput (2024-2025):** PutEvents throughput
  increased; lower latency for real-time recommendation updates.

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

## Error handling

### Solution version CREATE_FAILED
- Insufficient training data (fewer than ~1000 interactions). Add more
  data and re-import. Check the error message for specifics.

### Campaign CREATE_PENDING
- The solution version is not yet ACTIVE. Wait for training to complete
  (check `describe-solution-version`), then create the campaign.

### InvalidInputException on import job
- The CSV headers do not match the schema, or a column has the wrong
  type. Validate the CSV against the schema before importing.

### ResourceNotFoundException on PutEvents
- The tracking ID is wrong, or the event tracker was recreated. Update
  the client with the new tracking ID.

### Filter InvalidFilterExpression
- The filter expression has a syntax error or references a column not
  in the dataset. Review the Personalize filter-expression syntax.

### Campaign UPDATE_PENDING
- The campaign is updating to a new solution version. Wait ~15 minutes
  for the update to complete. GetRecommendations continues to work
  (serving the previous version) during the update.

### High cost on the bill
- minProvisionedTPS is set higher than needed. Reduce it via
  `update-campaign --min-provisioned-tps`. Auto-scaling handles spikes
  above the floor.

## Domain

AWS CloudOps / Amazon Personalize Recommendation System Provisioning.

## AWS documentation

- **Personalize Developer Guide** — https://docs.aws.amazon.com/personalize/latest/dg/
- **Dataset groups** — https://docs.aws.amazon.com/personalize/latest/dg/dataset-groups.html
- **Schemas and datasets** — https://docs.aws.amazon.com/personalize/latest/dg/data-prep-formatting.html
- **Recipes** — https://docs.aws.amazon.com/personalize/latest/dg/working-with-predefined-recipes.html
- **User-Personalization recipe** — https://docs.aws.amazon.com/personalize/latest/dg/native-recipe-new-item-USER_PERSONALIZATION.html
- **Campaigns** — https://docs.aws.amazon.com/personalize/latest/dg/campaigns.html
- **Event tracker and PutEvents** — https://docs.aws.amazon.com/personalize/latest/dg/recording-events.html
- **Batch inference jobs** — https://docs.aws.amazon.com/personalize/latest/dg/getting-batch-recommendations.html
- **Domain recommenders** — https://docs.aws.amazon.com/personalize/latest/dg/domain-recommenders.html
- **Filters** — https://docs.aws.amazon.com/personalize/latest/dg/filter.html
- **Solution metrics** — https://docs.aws.amazon.com/personalize/latest/dg/working-with-training-metrics.html
- **Pricing (minProvisionedTPS)** — https://aws.amazon.com/personalize/pricing/
