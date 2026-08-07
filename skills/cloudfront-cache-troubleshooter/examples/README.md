# End-to-end usage scenario: cloudfront-cache-troubleshooter

A walkthrough showing the skill diagnosing a CloudFront cache miss
caused by an S3 origin sending `Cache-Control: no-store`. This exercises
Step 1 (symptom identification), Step 2 (CACHE_MISS_ALWAYS), the
origin-header-vs-policy-precedence rule, and the remediation workflow.

## Input (user prompt)

> Our `d123.cloudfront.net` distribution is not caching anything. Every
> request shows `x-cache: Miss from cloudfront`. We're using the
> `CachingOptimized` managed policy with a 24-hour TTL. The origin is
> an S3 bucket. `curl -I` to the S3 bucket shows
> `Cache-Control: no-store`. Origin load is through the roof.

## Skill output

```text
DISTRIBUTION: E1A2B3C4D5 (d123.cloudfront.net)
VERDICT: ROOT_CAUSE_FOUND
ROOT_CAUSE: ORIGIN_NO_STORE — the S3 origin returns
  "Cache-Control: no-store" on all objects, which instructs CloudFront
  never to cache. The CachingOptimized policy's TTL is overridden by
  the origin's no-store directive (the policy is set to respect origin
  cache control headers).
CACHE_ISSUE: ORIGIN_NO_STORE
EVIDENCE:
  - curl -I to S3 origin (my-content-bucket.s3.amazonaws.com/index.html):
    response includes "Cache-Control: no-store"
  - curl -I to CloudFront (d123.cloudfront.net/index.html): "x-cache:
    Miss from cloudfront", "Age: 0"
  - get-cache-policy (CachingOptimized, 658327ea-...): MinTTL=1,
    DefaultTTL=86400, MaxTTL=31536000 — policy TTL is correct; origin
    header overrides it
  - get-distribution-config: no Lambda@Edge, no WAF, single S3 origin
  - CloudFront access logs: x-edge-result-type "Miss" on 100% of
    requests
ROOT_CAUSE_CATALOG: #1 (origin sends no-store)
REMEDIATION:
  1. Update the S3 object metadata to remove no-store and set a
     positive max-age. For existing objects, use s3api copy-object with
     metadata-directive REPLACE:
     aws s3api copy-object --bucket my-content-bucket --key index.html \
       --copy-source my-content-bucket/index.html \
       --cache-control "public, max-age=86400" \
       --metadata-directive REPLACE
  2. For bulk update across all objects in the bucket, use an S3 batch
     operation or a script:
     for key in $(aws s3api list-objects-v2 --bucket my-content-bucket \
       --query 'Contents[*].Key' --output text); do
       aws s3api copy-object --bucket my-content-bucket --key "$key" \
         --copy-source "my-content-bucket/$key" \
         --cache-control "public, max-age=86400" \
         --metadata-directive REPLACE
     done
  3. Verify the origin header:
     curl -sI https://my-content-bucket.s3.amazonaws.com/index.html \
       | grep -i cache-control
     Expect: "Cache-Control: public, max-age=86400"
  4. Request via CloudFront twice; the second request should be a Hit:
     curl -sI https://d123.cloudfront.net/index.html | grep -i x-cache
     Expect: "x-cache: Hit from cloudfront" on the second request.
  5. Monitor CacheHitRate over the next hour; expect > 90%.
```

## What the skill caught that a generic assistant misses

1. **The origin-header-vs-policy-precedence rule.** A generic assistant
   sees "CachingOptimized with 24-hour TTL" and concludes "the policy is
   correct, the caching should work." The skill recognises that the
   origin's `Cache-Control: no-store` overrides the policy TTL because
   `OriginCacheControlHeaders: respect` is the default. The fix is on the
   origin, not the policy.

2. **The `no-store` vs `no-cache` distinction.** A generic assistant
   treats both as "caching is off." The skill distinguishes: `no-store`
   means CloudFront must not store the response at all; `no-cache` means
   CloudFront may store but must revalidate. The remediation differs.

3. **The S3 metadata fix.** A generic assistant recommends "change the
   origin header" without specifying how. The skill provides the exact
   `s3api copy-object --metadata-directive REPLACE` command, which is the
   only way to update metadata on an existing S3 object.

4. **The bulk-update pattern.** A generic assistant fixes one object. The
   skill provides a loop script for bulk-updating all objects in the
   bucket, because the `no-store` header was on "all objects" per the
   symptom.

## Slash-command invocation

```
/aws:troubleshoot-cloudfront-cache
```

Or via the orchestrator:

```
/aws:pipeline
You: "d123.cloudfront.net is not caching, every request is a Miss, origin is S3"
```

The orchestrator emits `[Phase: Troubleshoot | Skills routed:
cloudfront-cache-troubleshooter]` and hands off to this skill for the
VERDICT.

## CLI routing

```bash
node cli/bin/cli.js route "CloudFront cache miss every request, x-cache Miss from cloudfront"
# [Phase: Troubleshoot | Skills routed: cloudfront-cache-troubleshooter]
```

## Live-account diagnostic flow (requires AWS CLI)

When the operator has credentials for the failing distribution:

```bash
# Check the origin's Cache-Control directly.
curl -sI https://my-content-bucket.s3.amazonaws.com/index.html \
  | grep -iE 'cache-control|set-cookie'

# Check the cache policy TTL and OriginCacheControlHeaders setting.
aws cloudfront get-cache-policy --id 658327ea-f89d-4fab-a63d-7e88639e58f6 \
  --query 'CachePolicy.CachePolicyConfig.{minTTL:MinTTL,defaultTTL:DefaultTTL,maxTTL:MaxTTL,originCC:OriginCacheControlHeaders}' \
  --output json

# Test via CloudFront: request twice, check if second is Hit.
curl -sI https://d123.cloudfront.net/index.html | grep -iE 'x-cache|age'
curl -sI https://d123.cloudfront.net/index.html | grep -iE 'x-cache|age'
```

If the origin sends `Cache-Control: no-store` and CloudFront shows `Miss`
on every request with `Age: 0`, the diagnosis is confirmed as
ORIGIN_NO_STORE. The fix is to update the origin's Cache-Control header;
no cache policy change is needed.
