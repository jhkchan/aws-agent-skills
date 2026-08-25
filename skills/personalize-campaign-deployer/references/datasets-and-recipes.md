# Datasets, Schemas, and Recipes — Personalize Campaign Deployer

Deep reference on dataset group types (CUSTOM vs DOMAIN), dataset
schemas (Avro-like JSON), bulk import from S3, IAM service roles,
recipe selection (User-Personalization, SIMS, Popularity-Counting,
Personalized-Ranking, Item-Attribute-Affinity), HPO vs manual
training, and solution-version management. Loaded on demand by the
skill — kept out of the main SKILL.md body so the provisioning
procedure stays scannable.

## Dataset group types

### CUSTOM vs DOMAIN

| Type | Use | Downstream |
|---|---|---|
| CUSTOM | Full control over recipe and configuration | Solutions + campaigns |
| ECOMMERCE | Online retail | Pre-built recommenders (Recommended For You, FBT, etc.) |
| VIDEO | Streaming video | Pre-built recommenders (Because You Watched, Top Picks) |
| MUSIC | Audio / music streaming | Pre-built recommenders |

DOMAIN groups are faster to deploy and use AWS-optimized recipes.
CUSTOM groups are for non-standard domains or custom recipes.

```bash
# CUSTOM
aws personalize create-dataset-group --name retail-recs --domain CUSTOM --region us-east-1

# DOMAIN (ECOMMERCE)
aws personalize create-dataset-group --name shop-recs --domain ECOMMERCE --region us-east-1
```

## Datasets and schemas

### Dataset types

| Dataset | Required? | Required fields | Common optional fields |
|---|---|---|---|
| Interactions | YES | USER_ID, ITEM_ID, TIMESTAMP | EVENT_TYPE, EVENT_VALUE, IMPRESSION, RESERVATION |
| Users | No | USER_ID | AGE, GENDER, LOCATION, etc. |
| Items | No | ITEM_ID | CATEGORY, PRICE, GENRE, etc. |

### Interactions schema (full example)

```json
{
  "type": "record",
  "name": "Interactions",
  "namespace": "com.amazonaws.personalize.schema",
  "fields": [
    {"name": "USER_ID", "type": "string"},
    {"name": "ITEM_ID", "type": "string"},
    {"name": "TIMESTAMP", "type": "long"},
    {"name": "EVENT_TYPE", "type": "string"},
    {"name": "EVENT_VALUE", "type": "float"},
    {"name": "IMPRESSION", "type": "string", "categorical": true}
  ],
  "version": "1.0"
}
```

### Users schema example

```json
{
  "type": "record",
  "name": "Users",
  "namespace": "com.amazonaws.personalize.schema",
  "fields": [
    {"name": "USER_ID", "type": "string"},
    {"name": "AGE", "type": "int"},
    {"name": "GENDER", "type": "string", "categorical": true}
  ],
  "version": "1.0"
}
```

### Items schema example

```json
{
  "type": "record",
  "name": "Items",
  "namespace": "com.amazonaws.personalize.schema",
  "fields": [
    {"name": "ITEM_ID", "type": "string"},
    {"name": "CATEGORY", "type": "string", "categorical": true},
    {"name": "PRICE", "type": "float"},
    {"name": "GENRE", "type": "string", "categorical": true}
  ],
  "version": "1.0"
}
```

**Critical:** schemas are IMMUTABLE after creation. To add columns,
create a new schema and dataset, then re-import data.

### Schema creation CLI

```bash
# Create the schema
SCHEMA_ARN=$(aws personalize create-schema \
  --name interactions-schema \
  --schema file://interactions-schema.json \
  --region us-east-1 \
  --query 'schemaArn' --output text)

# Create the dataset referencing the schema
aws personalize create-dataset \
  --name interactions \
  --dataset-group-arn <dataset-group-arn> \
  --dataset-type INTERACTIONS \
  --schema-arn "$SCHEMA_ARN" \
  --region us-east-1
```

### CSV formatting

The CSV must have headers matching the schema field names (case-
sensitive). For categorical fields, separate multiple values with
`|` (e.g., `Action|Comedy` for GENRE).

```csv
USER_ID,ITEM_ID,TIMESTAMP,EVENT_TYPE,EVENT_VALUE
user-001,item-100,1722816000,click,1.0
user-001,item-200,1722816060,purchase,1.0
user-002,item-100,1722816120,view,1.0
```

## Bulk data import from S3

### IAM service role

The Personalize service assumes a role to read from S3. Two policies
are required: a trust policy and a permission policy.

**Trust policy:**

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {"Service": "personalize.amazonaws.com"},
      "Action": "sts:AssumeRole"
    }
  ]
}
```

**Permission policy:**

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": "s3:GetObject",
      "Resource": "arn:aws:s3:::my-training-data/*"
    },
    {
      "Effect": "Allow",
      "Action": "s3:ListBucket",
      "Resource": "arn:aws:s3:::my-training-data"
    }
  ]
}
```

### Import job CLI

```bash
aws personalize create-dataset-import-job \
  --job-name interactions-import-001 \
  --dataset-arn <dataset-arn> \
  --data-source '{"dataLocation":"s3://my-training-data/interactions.csv"}' \
  --role-arn arn:aws:iam::123456789012:role/PersonalizeS3ReadRole \
  --region us-east-1
```

### Import job status

```bash
aws personalize describe-dataset-import-job \
  --dataset-import-job-arn <import-job-arn> \
  --query 'datasetImportJob.status' --region us-east-1
# CREATE PENDING → IN PROGRESS → ACTIVE
```

Wait for ACTIVE before creating a solution. Training against a
partially-imported dataset produces poor recommendations.

## Recipe reference

### CUSTOM recipes

| Recipe ARN | Use case | Event tracker | Cold start |
|---|---|---|---|
| aws-user-personalization | Personalized recs (90% of cases) | Yes | Yes |
| aws-sims | Item-to-item similarity | No | No |
| aws-popularity-counting | Most-popular baseline | No | No |
| aws-personalized-ranking | Re-rank a candidate list | Yes | Yes |
| aws-item-attribute-affinity | Item affinity by attribute | No | N/A |

### DOMAIN recipes (ECOMMERCE)

| Recipe ARN | Use case |
|---|---|
| aws-ecomm-recommended-for-you | Personalized "for you" |
| aws-ecomm-users-who-viewed-x-also-viewed | Item-to-item |
| aws-ecomm-frequently-bought-together | Cross-sell |
| aws-ecomm-popular-items-by-views | Trending by views |
| aws-ecomm-popular-items-by-purchases | Best sellers |
| aws-ecomm-most-purchased | All-time most purchased |

### DOMAIN recipes (VIDEO)

| Recipe ARN | Use case |
|---|---|
| aws-video-recommended-for-you | Personalized |
| aws-video-because-you-watched | Item-to-item |
| aws-video-top-picks | Curated top |
| aws-video-continue-watching | Resume watching |

## Solution and solution version

### Create solution

```bash
aws personalize create-solution \
  --name user-personalization-solution \
  --dataset-group-arn <dataset-group-arn> \
  --recipe-arn arn:aws:personalize:::recipe/aws-user-personalization \
  --region us-east-1
```

### Solution version (training modes)

| Mode | Description | When to use |
|---|---|---|
| FULL | Train from scratch | First training, major data refresh |
| UPDATE | Incremental update | Minor data additions (faster) |

### HPO (Hyperparameter Optimization)

```bash
aws personalize create-solution-version \
  --solution-arn <solution-arn> \
  --training-mode FULL \
  --perform-hpo \
  --region us-east-1
```

HPO explores the hyperparameter space and may produce better metrics,
but takes significantly longer. Without `--perform-hpo`, Personalize
uses the recipe's default hyperparameters.

### AutoTraining

```bash
aws personalize update-solution \
  --solution-arn <solution-arn> \
  --perform-auto-training \
  --solution-update-config '{"autoTrainingConfig":{"schedulingExpression":"rate(7 days)"}}' \
  --region us-east-1
```

AutoTraining creates a new solution version on a schedule (e.g., every
7 days). To deploy the new version, call `update-campaign`.

### Solution version status

```bash
aws personalize describe-solution-version \
  --solution-version-arn <arn> \
  --query 'solutionVersion.status' --region us-east-1
# CREATE PENDING → IN PROGRESS → ACTIVE | CREATE FAILED
```

Training time: typically 30 minutes to several hours, depending on
data volume and HPO.

## Common pitfalls

### Schema mismatch on import
- CSV headers do not match the schema field names (case-sensitive).
- A column has the wrong type (e.g., string where the schema says long).
- Categorical fields are not pipe-separated.

### Insufficient training data
- Fewer than ~1000 interactions. Personalize recommends at least 1000.
- Single-event-type data (e.g., only "view" events) limits recipe
  effectiveness.

### Wrong recipe for the use case
- SIMS used for user-personalization (it is item-to-item, not user).
- Popularity-Counting used as production (it is a baseline, not
  personalized).
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

