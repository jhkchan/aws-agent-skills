---
name: troubleshoot-cloudfront-cache
description: >-
  Slash command for the cloudfront-cache-troubleshooter skill. Diagnoses
  CloudFront caching issues including cache misses on every request, stale
  content, cache key variation, 403/404 from cache, and low hit ratio via
  a symptom-to-cause decision tree. Emits ROOT_CAUSE_FOUND |
  NEED_MORE_INFO | ESCALATE with the specific cache issue type and
  evidence.
skill: cloudfront-cache-troubleshooter
family: Networking
task_type: troubleshoot
verdict_shape: "ROOT_CAUSE_FOUND | NEED_MORE_INFO | ESCALATE"
allowed-tools: Read, Bash, Grep, Glob
---

# /aws:troubleshoot-cloudfront-cache

Invoke the `cloudfront-cache-troubleshooter` skill to diagnose a
CloudFront caching incident.

Read the skill at `skills/cloudfront-cache-troubleshooter/SKILL.md` and
follow its diagnostic procedure to identify the root cause.

## When to use

- CloudFront returns `x-cache: Miss from cloudfront` on every request.
- Content is stale (origin updated but CloudFront serves the old version).
- Same URL serves different content to different users (cache key
  variation).
- CloudFront returns 403/404 when the origin returns 200.
- Cache hit ratio is dropping or origin load is elevated.
- Lambda@Edge or WAF may be interfering with caching.
- Compressed content is not served correctly (`Accept-Encoding` not in
  cache key).

## Invocation

```
/aws:troubleshoot-cloudfront-cache <distribution ID / domain / symptom description>
```

The skill will:

1. Identify the symptom category (CACHE_MISS_ALWAYS, STALE_CONTENT,
   CACHE_KEY_VARIATION, ERROR_FROM_CACHE, LOW_HIT_RATIO).
2. Request the distribution ID and `curl -I` response headers from both
   CloudFront and the origin.
3. Walk the category-specific diagnostic tree.
4. Cross-reference with cache policy, CloudFront access logs, WAF rules,
   and Lambda@Edge functions as required by the category.
5. Map to the common root-cause catalog (10 patterns covering the
   majority of CloudFront caching incidents).
6. Verify the proposed fix with `curl -I` before applying.
7. Emit the standard VERDICT block.

## Output shape

```text
DISTRIBUTION: <distribution ID or domain>
VERDICT: ROOT_CAUSE_FOUND | NEED_MORE_INFO | ESCALATE
ROOT_CAUSE: <cache issue name> — <specific root cause>
CACHE_ISSUE: <ORIGIN_NO_STORE | CACHE_KEY_BLOAT | WAF_BLOCK | ...>
EVIDENCE:
  - <origin response header>: <value>
  - <cache policy field>: <value>
  - <x-edge-result-type from access logs>: <value>
ROOT_CAUSE_CATALOG: #<N>
REMEDIATION: <specific config change + verification command>
```

## Pre-flight

The skill requires the distribution ID or domain name. Ideally the
operator also provides the `curl -I` response headers from both
CloudFront and the origin, the cache policy details, and access log
excerpts. If the distribution ID is unknown, the skill will run
`aws cloudfront list-distributions` to locate it by domain or alias. If
the user provides only a vague symptom with no identifying info, the
skill emits `NEED_MORE_INFO`.

## References

- Skill: `skills/cloudfront-cache-troubleshooter/SKILL.md`
- Reference: `skills/cloudfront-cache-troubleshooter/references/cache-key-model.md`
- Reference: `skills/cloudfront-cache-troubleshooter/references/diagnostic-commands.md`
- AWS docs: https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/ConfiguringCaching.html
