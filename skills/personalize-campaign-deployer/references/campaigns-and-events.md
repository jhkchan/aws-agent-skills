# Campaigns, Event Trackers, and Real-Time — Personalize Campaign Deployer

Deep reference on campaign creation (minProvisionedTPS, campaign
config, update), event tracker deployment (PutEvents integration
patterns, Lambda handlers, one-tracker-per-group), batch inference
jobs, recommender configuration for DOMAIN groups, filter expressions,
solution metrics, and cost optimization. Loaded on demand by the
skill — kept out of the main SKILL.md body so the provisioning
procedure stays scannable.

## Campaign creation and management

### Create campaign

```bash
aws personalize create-campaign \
  --name retail-campaign \
  --solution-version-arn <solution-version-arn> \
  --min-provisioned-tps 1 \
  --campaign-config '{"itemExplorationConfig":{"coldItemRelativeWeight":0.1,"enableMetadataWithRecommendations":true}}' \
  --region us-east-1
```

### Campaign config

| Field | Description |
|---|---|
| `itemExplorationConfig.coldItemRelativeWeight` | Weight for cold-start items (0.0-1.0; higher = more exploration) |
| `itemExplorationConfig.enableMetadataWithRecommendations` | Return item metadata in GetRecommendations response |

### minProvisionedTPS cost math

```
Cost (illustrative, us-east-1):
  minProvisionedTPS = 1  → ~$0.20/hour  → ~$150/month
  minProvisionedTPS = 5  → ~$1.00/hour  → ~$730/month
  minProvisionedTPS = 10 → ~$2.00/hour  → ~$1460/month
  minProvisionedTPS = 50 → ~$10.00/hour → ~$7300/month

The campaign auto-scales ABOVE minProvisionedTPS during traffic spikes
(billed per-transaction). You only pay the floor for idle capacity.
```

**Strategy:** start at 1 for dev/staging. For production, set to your
p50 (median) TPS. Update without deleting:

```bash
aws personalize update-campaign \
  --campaign-arn <campaign-arn> \
  --min-provisioned-tps 5 \
  --region us-east-1
```

### Update campaign (new solution version)

```bash
aws personalize update-campaign \
  --campaign-arn <campaign-arn> \
  --solution-version-arn <new-solution-version-arn> \
  --region us-east-1
```

Update takes ~15 minutes. The campaign is briefly in UPDATE_PENDING.
GetRecommendations continues serving the previous version during the
update.

### GetRecommendations

```bash
aws personalize-runtime get-recommendations \
  --campaign-arn <campaign-arn> \
  --user-id user-123 \
  --num-results 10 \
  --region us-east-1

# With filter
aws personalize-runtime get-recommendations \
  --campaign-arn <campaign-arn> \
  --user-id user-123 \
  --filter-arn <filter-arn> \
  --region us-east-1
```

### Campaign status

```bash
aws personalize describe-campaign \
  --campaign-arn <campaign-arn> \
  --query 'campaign.status' --region us-east-1
# CREATE PENDING → IN PROGRESS → ACTIVE | UPDATE PENDING | CREATE FAILED
```

## Event tracker and PutEvents

### Create event tracker

```bash
TRACKING_ID=$(aws personalize create-event-tracker \
  --name retail-event-tracker \
  --dataset-group-arn <dataset-group-arn> \
  --region us-east-1 \
  --query 'trackingId' --output text)

echo "Tracking ID: $TRACKING_ID"
```

**Critical:** only ONE active event tracker per dataset group.
Recreating invalidates the previous tracking ID — all clients using
the old ID will fail with ResourceNotFoundException.

### PutEvents patterns

**Lambda handler (S3 trigger or API Gateway):**

```python
import json
import boto3
from datetime import datetime

personalize_events = boto3.client("personalize-events")
TRACKING_ID = "abc123-tracking-id"  # from create-event-tracker

def lambda_handler(event, context):
    for record in event.get("Records", []):
        body = json.loads(record["body"]) if "body" in record else record
        personalize_events.put_events(
            trackingId=TRACKING_ID,
            userId=body["user_id"],
            sessionId=body["session_id"],
            eventList=[{
                "eventId": body.get("event_id", ""),
                "eventType": body["event_type"],   # "click", "view", "purchase"
                "itemId": body["item_id"],
                "sentAt": int(datetime.utcnow().timestamp()),
                "properties": json.dumps({
                    "event_value": float(body.get("event_value", 1.0))
                })
            }]
        )
    return {"statusCode": 200}
```

**Browser SDK pattern (real-time click stream):**

```javascript
// AWS SDK v3 in browser
import { PersonalizeEventsClient, PutEventsCommand } from "@aws-sdk/client-personalize-events";

const client = new PersonalizeEventsClient({ region: "us-east-1" });

await client.send(new PutEventsCommand({
  trackingId: TRACKING_ID,
  userId: currentUserId,
  sessionId: currentSessionId,
  eventList: [{
    eventId: crypto.randomUUID(),
    eventType: "click",
    itemId: clickedItemId,
    sentAt: Date.now() / 1000,
  }]
}));
```

### IAM for PutEvents

The Lambda (or browser role, via Cognito) needs:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": "personalize-events:PutEvents",
      "Resource": "*"
    }
  ]
}
```

### Event types and their impact

| Event type | Signal strength | Notes |
|---|---|---|
| `click` | Medium | User showed interest |
| `view` | Low | Weak signal; pair with dwell time |
| `purchase` | High | Strongest signal |
| `add-to-cart` | Medium-High | Strong intent |
| `rate` | Configurable | Use EVENT_VALUE for the rating |

Personalize weights different event types via the `EVENT_VALUE` field
and the recipe's event-type weighting (configurable during solution
creation for some recipes).

## Batch inference jobs

### Create batch inference job

```bash
aws personalize create-batch-inference-job \
  --job-name nightly-recommendations-2026-08-05 \
  --solution-version-arn <solution-version-arn> \
  --job-input '{"s3DataSource":{"path":"s3://batch-input/users.json"}}' \
  --job-output '{"s3DataDestination":{"path":"s3://batch-output/recs/"}}' \
  --role-arn arn:aws:iam::123456789012:role/PersonalizeBatchRole \
  --num-results 25 \
  --region us-east-1
```

### Input format (JSON Lines)

```json
{"userId": "user-001"}
{"userId": "user-002"}
{"userId": "user-003"}
```

### Output format

Per-user recommendation JSON written to the S3 output path. Each file
contains the ranked item list with scores.

### Batch role

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["s3:GetObject", "s3:PutObject"],
      "Resource": ["arn:aws:s3:::batch-input/*", "arn:aws:s3:::batch-output/*"]
    },
    {
      "Effect": "Allow",
      "Action": "s3:ListBucket",
      "Resource": ["arn:aws:s3:::batch-input", "arn:aws:s3:::batch-output"]
    }
  ]
}
```

## Recommenders (DOMAIN groups)

### Create recommender

```bash
aws personalize create-recommender \
  --name recommended-for-you \
  --dataset-group-arn <ecommerce-dataset-group-arn> \
  --recipe-arn arn:aws:personalize:::recipe/aws-ecomm-recommended-for-you \
  --recommender-config '{"minRecommendationRequestsPerSecond": 1}' \
  --region us-east-1
```

`minRecommendationRequestsPerSecond` is the DOMAIN equivalent of
minProvisionedTPS — it sets the cost floor.

### GetRecommendations with recommender

```bash
aws personalize-runtime get-recommendations \
  --recommender-arn <recommender-arn> \
  --user-id user-123 \
  --num-results 10 \
  --region us-east-1
```

For item-to-item recommenders (e.g., Users Who Viewed X Also Viewed):

```bash
aws personalize-runtime get-recommendations \
  --recommender-arn <recommender-arn> \
  --item-id item-789 \
  --num-results 10 \
  --region us-east-1
```

## Filters

### Filter expressions

| Expression | Purpose |
|---|---|
| `EXCLUDE ItemID WHERE Items.IN_STOCK IN ("false")` | Exclude out-of-stock |
| `INCLUDE ItemID WHERE Items.CATEGORY IN ("electronics")` | Category-only recs |
| `EXCLUDE ItemID WHERE Interactions.EVENT_TYPE IN ("purchase")` | Exclude already-purchased |

### Create filter

```bash
aws personalize create-filter \
  --name exclude-out-of-stock \
  --dataset-group-arn <dataset-group-arn> \
  --filter-expression 'EXCLUDE ItemID WHERE Items.IN_STOCK IN ("false")' \
  --region us-east-1
```

### Apply filter at GetRecommendations

```bash
aws personalize-runtime get-recommendations \
  --campaign-arn <campaign-arn> \
  --user-id user-123 \
  --filter-arn <filter-arn> \
  --region us-east-1
```

### Dynamic filters (with parameters)

For filters that need runtime values (e.g., exclude items in the
user's cart):

```bash
aws personalize-runtime get-recommendations \
  --campaign-arn <campaign-arn> \
  --user-id user-123 \
  --filter-arn <filter-arn> \
  --filter-values '{"CART_ITEMS": "item-1,item-2,item-3"}' \
  --region us-east-1
```

The filter expression uses `$CART_ITEMS` placeholder:

```
EXCLUDE ItemID WHERE ItemID IN ($CART_ITEMS)
```

## Solution metrics

### Get metrics

```bash
aws personalize get-solution-metrics \
  --solution-version-arn <solution-version-arn> \
  --region us-east-1
```

### Metric definitions

| Metric | Range | Description |
|---|---|---|
| `coverage` | 0.0-1.0 | Fraction of catalog items recommended |
| `mean_reciprocal_rank` (MRR) | 0.0-1.0 | Average reciprocal rank of first relevant rec |
| `normalized_discounted_cumulative_gain` (NDCG) | 0.0-1.0 | Ranking quality (rewards relevant items at top) |
| `precision_at_k` | 0.0-1.0 | Fraction of top-k recs that are relevant |
| `recall_at_k` | 0.0-1.0 | Fraction of relevant items in top-k |

Higher is better for all metrics. Typical production targets:
- precision_at_k >= 0.05-0.20 (varies by domain)
- NDCG >= 0.10-0.30
- coverage >= 0.30 (avoid over-concentration on popular items)

### Tuning low metrics

If metrics are low after training:
1. Increase interaction data volume (more events, more users).
2. Verify EVENT_TYPE distribution (mix of view/click/purchase).
3. Enable HPO for the next training.
4. Try a different recipe (e.g., Personalized-Ranking if you have a
   candidate list to re-rank).
5. Add Users and Items datasets for metadata signals.

## Cost optimization

### minProvisionedTPS
- Start at 1 for dev/staging.
- Set to p50 TPS for production.
- Update via `update-campaign` without recreating.

### AutoTraining schedule
- Less frequent (every 30 days) for stable catalogs.
- More frequent (every 7 days) for fast-changing catalogs.

### Batch vs real-time
- Batch inference is cheaper for offline scoring of large user lists.
- Use real-time campaigns only for online serving that needs < 100ms
  latency.

### Event tracker
- PutEvents is billed per-event (much cheaper than retraining).
- Use PutEvents for incremental updates; reserve full retraining for
  major data refreshes.
