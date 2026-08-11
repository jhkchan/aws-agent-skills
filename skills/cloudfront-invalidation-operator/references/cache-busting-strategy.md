# CloudFront Cache-Busting Strategy Reference

Load this reference when deciding between invalidation and versioned
filenames for cache-busting. The matrix below shows which strategy to
use for each scenario.

## Strategy comparison matrix

| Strategy | Cost | Speed | Complexity | Best for |
|---|---|---|---|---|
| **Versioned filenames** (`app.<hash>.js`) | Free | Instant (new URL = fresh fetch) | Medium (build pipeline change) | Routine deploys, CI/CD, static assets |
| **Cache-Control: max-age=0** | Free | Instant (no cache) | Low | Dynamic content, APIs |
| **`/*` invalidation** | Free (1 path) | 10-120 seconds | Low | Emergency content removal, hotfixes |
| **Directory wildcard** (`/images/*`) | Free (1 path) | 10-60 seconds | Low | Partial site updates |
| **Individual path invalidation** | Free or $0.005/path | 10-60 seconds | High (path enumeration) | Targeted removal of specific objects |
| **CloudFront Function URL rewrite** | Free | Instant | High | Dynamic version injection |

## When to use invalidation

Use invalidation when:

1. **Sensitive data was cached** and must be removed from edge
   locations immediately (e.g., a private document was accidentally
   published and cached).
2. **An unversioned HTML file was updated** (e.g., `index.html`
   changed but the filename has no hash).
3. **A hotfix was deployed** to an unversioned asset and users need
   the fix immediately.
4. **Error pages were cached** and need to be cleared (e.g., a 503
   was cached during an outage and persists after recovery).
5. **A continuous deployment test** requires clearing the staging
   distribution's edge cache.

## When to use versioned filenames instead

Use versioned filenames when:

1. **Routine CI/CD deploys** — the build process appends a content
   hash (`app.a1b2c3.js`). The new filename is a new URL; CloudFront
   fetches it from the origin on first request. No invalidation
   needed.
2. **Static assets** (JS, CSS, images) that change on every deploy.
3. **Long cache TTLs** are desired (years) for immutable assets.
4. **Cost optimization** — avoid burning the 1,000-path free tier on
   routine deploys.

### Versioned filename setup

```bash
# Build pipeline: append content hash to filenames
# Webpack/Vite/Rollup all support this via output.filename:
#   output: { filename: '[name].[contenthash].8.js' }

# Reference the hashed filenames in HTML:
#   <script src="/js/main.a1b2c3d4.js"></script>

# Set long cache TTL for hashed assets:
#   Cache-Control: public, max-age=31536000, immutable

# For index.html (the entry point), use short TTL or invalidation:
#   Cache-Control: public, max-age=60
# (Or invalidate index.html on every deploy)
```

### S3 + CloudFront versioned filename workflow

```bash
# 1. Build with content-hashed filenames
npm run build  # produces dist/js/main.a1b2c3.js, dist/css/style.e5f6g7.css

# 2. Upload to S3 with long cache TTL for hashed assets
aws s3 sync dist/ s3://prod-bucket/ \
  --exclude "index.html" \
  --cache-control "public, max-age=31536000, immutable"

# 3. Upload index.html with short cache TTL
aws s3 cp dist/index.html s3://prod-bucket/index.html \
  --cache-control "public, max-age=60"

# 4. No invalidation needed for hashed assets (new URLs)
#    Optional: invalidate /index.html if TTL is long
aws cloudfront create-invalidation \
  --distribution-id E1ABC2DEF3GHI4 \
  --invalidation-batch '{"CallerReference":"deploy-'"$(date +%s)"'",
    "Paths":{"Quantity":1,"Items":["/index.html"]}}'
```

## CloudFront cache policy considerations

The cache policy determines how CloudFront caches objects:

| Policy setting | Effect on invalidation |
|---|---|
| **Min TTL: 0** | Objects can be evicted immediately; invalidation clears them |
| **Min TTL: 86400** (1 day) | CloudFront keeps objects for at least 1 day; invalidation overrides this |
| **Max TTL: 31536000** (1 year) | Objects cached up to 1 year; invalidation clears them early |
| **Default TTL: 3600** (1 hour) | Objects cached for 1 hour without explicit Cache-Control; invalidation clears them |

Invalidation always works regardless of cache policy TTLs. But if the
cache policy has a long Min TTL, you will need invalidation more often
unless you use versioned filenames.

## Browser cache vs CloudFront cache

| Cache layer | Cleared by invalidation? | How to bust |
|---|---|---|
| CloudFront edge cache | Yes | `create-invalidation` |
| Browser cache | No | Versioned filenames or `Cache-Control: no-cache` |
| Intermediate CDN (if chained) | No | Invalidate at the intermediate CDN |
| DNS resolver cache | No | Wait for TTL to expire or flush resolver |

**Key insight:** invalidation only clears CloudFront edge cache. If
users still see old content after invalidation, check:
1. Browser cache (hard refresh: Ctrl+Shift+R / Cmd+Shift+R)
2. Intermediate CDN (if using a CDN in front of CloudFront)
3. Origin content (verify the origin serves the updated content)
4. DNS resolution (if DNS was recently changed)

## Continuous deployment invalidation workflow

```bash
# 1. Identify primary and staging distribution IDs
POLICY=$(aws cloudfront get-continuous-deployment-policy \
  --id CDP1XYZ --output json)
STAGING_ID=$(echo $POLICY | jq -r '.ContinuousDeploymentPolicy.Staging')

# 2. Invalidate STAGING distribution (for testing)
aws cloudfront create-invalidation \
  --distribution-id $STAGING_ID \
  --invalidation-batch '{"CallerReference":"staging-'"$(date +%s)"'",
    "Paths":{"Quantity":1,"Items":["/*"]}}'

# 3. Test on staging DNS
curl -I https://<staging-dns>.cloudfront.net/index.html

# 4. If correct, promote staging to primary
#    (update-distribution to point to new config)
aws cloudfront get-distribution-config --id E1ABC2DEF3GHI4 > dist-config.json
# Edit dist-config.json to remove the staging reference and apply
aws cloudfront update-distribution \
  --id E1ABC2DEF3GHI4 \
  --if-match <etag> \
  --distribution-config file://dist-config.json

# 5. After promotion, invalidate PRIMARY if needed
aws cloudfront create-invalidation \
  --distribution-id E1ABC2DEF3GHI4 \
  --invalidation-batch '{"CallerReference":"primary-'"$(date +%s)"'",
    "Paths":{"Quantity":1,"Items":["/*"]}}'
```
