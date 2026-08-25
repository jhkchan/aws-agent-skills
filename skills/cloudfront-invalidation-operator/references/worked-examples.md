# Worked Examples (load on demand) — CloudFront Invalidation Operator

Worked examples moved verbatim from SKILL.md: specific-paths invalidation with cost advisory, wait-invalidation to COMPLETED, and continuous-deployment staging invalidation. The primary /* worked example remains in SKILL.md.


---

## Worked example — create-invalidation specific paths (cost advisory) (moved from SKILL.md)

```text
OPERATION: create-invalidation
VERDICT: READY
TARGET: E1ABC2DEF3GHI4 (domain: d111111abcdef8.cloudfront.net,
        account 111111111111)
PRE_CHECKS:
  - [PASS] Distribution exists, Status: Deployed
  - [PASS] Calling role has cloudfront:CreateInvalidation
  - [PASS] CallerReference: inv-20260810-002 (unique)
  - [WARN] Path count: 1,247 individual paths. Monthly cumulative:
    1,247 (247 paths beyond the 1,000 free-tier limit).
  - [WARN] Estimated cost: $0.005 x 247 = $1.24
  - [INFO] Consider replacing with /* (1 path, free) or
    /images/* + /css/* + /js/* (3 paths, free) if the majority of
    paths share common directory prefixes.
STEPS:
  1. CONFIRM: About to create a CloudFront invalidation on
     distribution E1ABC2DEF3GHI4 with 1,247 paths. Estimated cost:
     $1.24 (247 paths at $0.005 each beyond the free tier).
     Proceed? (yes/no)
  2. aws cloudfront create-invalidation \
       --distribution-id E1ABC2DEF3GHI4 \
       --invalidation-batch file://invalidation-batch.json
POST_VERIFY:
  - (pending execution)
COST: $1.24 (247 paths beyond free tier at $0.005/path)
NOTES:
  - Replacing the 1,247 individual paths with /* would cost $0.00
    (1 path, free tier). Consider this if all paths need clearing.
  - Replacing with /images/* + /css/* + /js/* (3 wildcard paths)
    would also be free. Consider if only these directories changed.
```


---

## Worked example — wait-invalidation (COMPLETED) (moved from SKILL.md)

```text
OPERATION: wait-invalidation
VERDICT: COMPLETED
TARGET: E1ABC2DEF3GHI4 (domain: d111111abcdef8.cloudfront.net)
PRE_CHECKS:
  - [PASS] Invalidation I2XYZ5678UVW90 exists
  - [PASS] InvalidationStatus: Completed
POST_VERIFY:
  - [PASS] InvalidationStatus: Completed (confirmed via
    get-invalidation)
  - [PASS] Invalidation appears in list-invalidations with Completed
  - [PASS] Spot-check: curl -I returns X-Cache: Miss from CloudFront
    (content re-fetched from origin)
COST: N/A (no new invalidation created)
NOTES:
  - Invalidation I2XYZ5678UVW90 completed in 47 seconds.
  - All edge locations have purged the specified paths.
  - Next viewer requests for these paths will fetch fresh content
    from the origin.
```


---

## Worked example — continuous deployment staging invalidation (moved from SKILL.md)

```text
OPERATION: create-invalidation
VERDICT: READY
TARGET: E1ABC2DEF3GHI4 (primary) + E5STAGING123 (staging, via
        continuous deployment policy CDP1XYZ)
PRE_CHECKS:
  - [PASS] Primary distribution exists, Status: Deployed
  - [PASS] ContinuousDeploymentPolicyId: CDP1XYZ (active)
  - [PASS] Staging distribution E5STAGING123 identified
  - [PASS] Calling role has cloudfront:CreateInvalidation on BOTH
    distribution ARNs
  - [PASS] Path pattern: /api/v2/* (valid wildcard)
  - [INFO] Plan: invalidate STAGING first, verify, then promote.
    After promotion, invalidate PRIMARY if needed.
STEPS:
  1. CONFIRM: About to create an invalidation on the STAGING
     distribution E5STAGING123 for /api/v2/*. This is a continuous
     deployment test. Proceed? (yes/no)
  2. aws cloudfront create-invalidation \
       --distribution-id E5STAGING123 \
       --invalidation-batch '{"CallerReference":"stg-20260810-001",
         "Paths":{"Quantity":1,"Items":["/api/v2/*"]}}'
  3. Verify staging serves fresh content via the staging DNS:
     curl -I https://<staging-dns>.cloudfront.net/api/v2/health
  4. If staging is correct, promote (update-distribution with the
     continuous deployment policy). Primary will serve the new
     content after promotion.
POST_VERIFY:
  - (pending execution)
COST: Free tier (1 path on staging, 1,000 monthly budget)
NOTES:
  - Continuous deployment staging invalidation is independent from
    the primary distribution's edge cache.
  - After promotion, the primary may need its own invalidation if
    the traffic shift causes cache misses.
  - Do NOT invalidate the primary before promoting — the primary
    still serves the old (stable) version until promotion.
```
