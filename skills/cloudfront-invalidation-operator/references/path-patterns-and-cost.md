# CloudFront Invalidation Path Patterns and Cost Reference

Load this reference when planning a CloudFront invalidation. The
tables below show path pattern syntax, cost calculations, and
wildcard optimization strategies.

## Path pattern syntax

| Pattern | Matches | Path count | Example |
|---|---|---|---|
| `/*` | All objects in the distribution | 1 | Clears entire edge cache |
| `/images/*` | All objects under `/images/` recursively | 1 | `/images/logo.png`, `/images/thumbnails/x.jpg` |
| `/images/*.jpg` | All `.jpg` files directly under `/images/` | 1 | `/images/photo.jpg` but NOT `/images/sub/photo.jpg` |
| `/index.html` | Single object | 1 | Exactly `/index.html` |
| `/css/*` | All objects under `/css/` recursively | 1 | `/css/main.css`, `/css/themes/dark.css` |
| `/api/v2/*` | All objects under `/api/v2/` | 1 | Used for API path invalidation |

## Invalid path patterns

| Pattern | Problem | Fix |
|---|---|---|
| `/images/*/photo.jpg` | Wildcard mid-segment (not supported) | Use `/images/*` to match the entire tree |
| `images/*` | Missing leading `/` | Add leading slash: `/images/*` |
| `/images photo.jpg` | Space in path (invalid) | URL-encode: `/images%20photo.jpg` |
| `/index.html?v=2` | Query string in path | Query strings are handled by cache-key policy, not invalidation |
| `/*/*` | Nested wildcards (not supported) | Use single `/*` (matches everything) |

## Cost calculation

### Free tier

- First **1,000** invalidation paths per month are free.
- Counted across ALL distributions in the account (not per-distribution).
- A wildcard path (`/*`, `/images/*`) counts as **1** path regardless
  of how many objects it matches.
- Reset on the 1st of each month.

### Beyond free tier

- **$0.005** per path per month for paths 1,001+.
- Individual object paths: each counts as 1 path.
- Wildcard paths: each counts as 1 path (regardless of match count).

### Cost examples

| Scenario | Paths | Cost |
|---|---|---|
| `/*` (monthly cumulative: 1) | 1 | $0.00 (free tier) |
| 500 individual paths (monthly cumulative: 500) | 500 | $0.00 (free tier) |
| 1,000 individual paths (monthly cumulative: 1,000) | 1,000 | $0.00 (free tier — exactly at limit) |
| 1,500 individual paths (monthly cumulative: 1,500) | 1,500 | $2.50 (500 x $0.005) |
| `/*` x 5 times in a month | 5 | $0.00 (free tier) |
| `/images/*` + `/css/*` + `/js/*` | 3 | $0.00 (free tier) |

### Wildcard optimization

When planning a bulk invalidation, compare the cost of individual
paths vs wildcards:

| Strategy | Paths | Cost | When to use |
|---|---|---|---|
| `/*` | 1 | Free | Need to clear everything (>60% of site) |
| `/images/*` + `/css/*` + `/js/*` | 3 | Free | Clearing specific directories |
| 500 individual paths | 500 | Free (if under 1,000 cumulative) | Targeted clearing of specific files |
| 1,247 individual paths | 1,247 | $1.24 | Replace with `/*` (free) if possible |
| 3,000 individual paths | 3,000 | $10.00 | Replace with `/*` + `/api/*` (2 paths, free) |

## Monthly cumulative tracking

Track cumulative path usage across all distributions:

```bash
# Get all distributions
DISTRIBUTIONS=$(aws cloudfront list-distributions \
  --query 'DistributionList.Items[*].Id' --output text)

TOTAL_PATHS=0
for DIST_ID in $DISTRIBUTIONS; do
  # Count paths invalidated this month
  PATHS=$(aws cloudfront list-invalidations \
    --distribution-id $DIST_ID \
    --query "InvalidationList.Items[?CreateTime>=\`$(date -u -v-1m +%Y-%m-%dT00:00:00Z)\`].InvalidationBatch.Paths.Quantity | sum(@)" \
    --output text 2>/dev/null || echo 0)
  echo "$DIST_ID: $PATHS paths this month"
  TOTAL_PATHS=$((TOTAL_PATHS + PATHS))
done

echo "Total paths this month: $TOTAL_PATHS"
echo "Free tier remaining: $((1000 - TOTAL_PATHS))"
if [ $TOTAL_PATHS -gt 1000 ]; then
  EXTRA=$((TOTAL_PATHS - 1000))
  echo "Cost beyond free tier: \$$((EXTRA * 5)) | 1000 | awk '{printf "%.2f", \$1/1000}'"
fi
```

## CallerReference best practices

- Use a **unique value per invalidation** — UUID, timestamp, or
  descriptive-with-timestamp (`inv-20260810-001`).
- CloudFront uses CallerReference for **idempotency**: reusing a value
  returns the original invalidation without creating a new one.
- Check `list-invalidations` to ensure CallerReference has not been
  used before.
- Do NOT use a static value like `"invalidation"` — this will cause
  all subsequent invalidations to silently deduplicate.

## Concurrent invalidation limits

- **15 concurrent InProgress** invalidations per distribution.
- Beyond 15: `TooManyInvalidationsInProgress` error.
- Fix: consolidate into fewer wildcard batches, or wait for existing
  invalidations to complete.
- Each `create-invalidation` API call supports up to **3,000 paths**
  (including wildcards).

## Diagnostic command quick-reference

| Goal | Command |
|---|---|
| Create invalidation | `aws cloudfront create-invalidation --distribution-id <id> --invalidation-batch file://batch.json` |
| Get invalidation status | `aws cloudfront get-invalidation --distribution-id <id> --id <inv-id>` |
| List invalidations | `aws cloudfront list-invalidations --distribution-id <id> --max-items 20` |
| Get distribution | `aws cloudfront get-distribution --id <id>` |
| List distributions | `aws cloudfront list-distributions --max-items 200` |
| Get continuous deployment policy | `aws cloudfront get-continuous-deployment-policy --id <policy-id>` |
| Update distribution (promote staging) | `aws cloudfront update-distribution --id <id> --if-match <etag> --distribution-config file://config.json` |
