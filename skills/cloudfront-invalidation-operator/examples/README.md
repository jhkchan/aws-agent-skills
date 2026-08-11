# End-to-end usage scenario: cloudfront-invalidation-operator

A walkthrough showing the skill planning a `/*` invalidation on a
Deployed CloudFront distribution, with all pre-checks passing and the
operator confirming at the CONFIRM gate. Contrasted with the BLOCKED
case where the distribution is Suspended.

## Input (user prompt)

> Invalidate the cache on distribution E1ABC2DEF3GHI4
> (d111111abcdef8.cloudfront.net). Clear everything — we deployed a
> broken build and need a full flush after fixing the origin.

```json
{
  "Operation": "create-invalidation",
  "DistributionId": "E1ABC2DEF3GHI4",
  "DomainName": "d111111abcdef8.cloudfront.net",
  "Paths": ["/*"],
  "Distribution": {
    "Status": "Deployed",
    "DistributionConfig": {"Enabled": true, "ContinuousDeploymentPolicyId": null}
  },
  "CallerReference": "inv-20260810-001",
  "MonthlyCumulativePaths": 12
}
```

## Skill output

```text
OPERATION: create-invalidation
VERDICT: READY
TARGET: E1ABC2DEF3GHI4 (domain: d111111abcdef8.cloudfront.net,
        account 111111111111)
PRE_CHECKS:
  - [PASS] Distribution exists
  - [PASS] Status: Deployed
  - [PASS] Enabled: true
  - [PASS] Path pattern: /* (valid — single wildcard path)
  - [PASS] Calling role has cloudfront:CreateInvalidation
  - [PASS] CallerReference: inv-20260810-001 (unique)
  - [INFO] Path count: 1 (free tier — 13 of 1,000 monthly paths)
STEPS:
  1. CONFIRM: About to create a CloudFront invalidation on
     distribution E1ABC2DEF3GHI4. Paths: /* (all objects). Cost:
     free tier. This will clear edge cache for ALL objects globally.
     Proceed? (yes/no)
  2. aws cloudfront create-invalidation \
       --distribution-id E1ABC2DEF3GHI4 \
       --invalidation-batch '{"CallerReference":"inv-20260810-001",
         "Paths":{"Quantity":1,"Items":["/*"]}}'
  3. Poll until Completed:
     aws cloudfront get-invalidation \
       --distribution-id E1ABC2DEF3GHI4 \
       --id <invalidation-id>
POST_VERIFY:
  - (pending execution)
COST: Free tier (1 path of 1,000 monthly)
NOTES:
  - /* invalidation counts as 1 path regardless of object count.
  - Propagation typically completes in 30-120 seconds globally.
  - Verify the origin serves the FIXED content before invalidating.
    Invalidation re-fetches from origin — if origin still has the
    broken build, the invalidation re-caches broken content.
```

## Contrast — BLOCKED case (Suspended distribution)

If the operator tried to invalidate a Suspended distribution, the
pre-check gate would fire and no CLI would execute:

```text
OPERATION: create-invalidation
VERDICT: BLOCKED
TARGET: E3SUSPENDED001 (domain: d333333suspend.cloudfront.net)
PRE_CHECKS:
  - [PASS] Distribution exists
  - [FAIL] Status: Suspended — cannot invalidate on a Suspended
    distribution. Restore via update-distribution with Enabled: true.
  - [FAIL] Enabled: false — distribution is disabled.
STEPS: (none — distribution not in Deployed state)
POST_VERIFY: (none)
COST: N/A (no invalidation created)
NOTES:
  - Root cause: the distribution is Suspended and disabled.
  - Fix: restore the distribution first:
    aws cloudfront get-distribution-config --id E3SUSPENDED001 > config.json
    # Edit config.json: set Enabled: true
    aws cloudfront update-distribution --id E3SUSPENDED001 \
      --if-match <etag> --distribution-config file://config.json
    # Wait for Status: Deployed, then re-attempt the invalidation.
```

## What the skill caught that a generic assistant misses

1. **Distribution status pre-check.** A generic assistant emits
   `create-invalidation` directly, which may fail silently on a
   Suspended distribution. The skill checks `Status: Deployed` first.

2. **Cost awareness.** A generic assistant does not mention the
   1,000-path free tier or the $0.005/path cost beyond it. The skill
   surfaces cost for every invalidation, especially bulk path lists.

3. **CallerReference uniqueness.** A generic assistant reuses the
   same CallerReference, causing silent deduplication. The skill
   verifies uniqueness against recent invalidations.

4. **Continuous deployment routing.** A generic assistant invalidates
   the primary distribution, missing the staging distribution. The
   skill identifies continuous deployment policies and routes to
   staging first.

5. **Cache-busting strategy recommendation.** A generic assistant
   suggests invalidation for every deploy. The skill recommends
   versioned filenames for routine deploys and reserves invalidation
   for emergencies.

6. **Origin health verification.** A generic assistant omits the
   critical step of verifying the origin has the correct content
   before invalidating. The skill explicitly warns: fix the origin
   first, then invalidate.

7. **Browser cache distinction.** A generic assistant conflates
   CloudFront cache with browser cache. The skill clarifies that
   invalidation only clears edge cache — browser cache requires
   versioned filenames or Cache-Control headers.

## Slash-command invocation

```
/aws:operate-cloudfront-invalidation
```

Or via the orchestrator:

```
/aws:pipeline
You: "invalidate /* on E1ABC2DEF3GHI4"
```

The orchestrator emits
`[Phase: Operate | Skills routed: cloudfront-invalidation-operator]`
and hands off to this skill for the VERDICT.

## CLI routing

```bash
node cli/bin/cli.js route "invalidate cache on E1ABC2DEF3GHI4"
# [Phase: Operate | Skills routed: cloudfront-invalidation-operator]
```

## Live-account follow-up (optional, requires AWS CLI)

After creating the invalidation:

```bash
# Poll for completion
INVALIDATION_ID="I2XYZ5678UVW90"
aws cloudfront get-invalidation \
  --distribution-id E1ABC2DEF3GHI4 \
  --id $INVALIDATION_ID \
  --query 'Invalidation.Status' \
  --profile default

# Spot-check: content re-fetched from origin
curl -I https://d111111abcdef8.cloudfront.net/index.html
# Look for: X-Cache: Miss from CloudFront

# Check monthly cumulative path count
aws cloudfront list-invalidations \
  --distribution-id E1ABC2DEF3GHI4 \
  --max-items 50 \
  --query 'InvalidationList.Items[*].InvalidationBatch.Paths.Quantity' \
  --output text \
  --profile default | tr '\t' '\n' | paste -sd+ | bc
```
