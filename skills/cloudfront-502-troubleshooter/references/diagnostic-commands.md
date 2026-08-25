# Diagnostic Commands (load on demand) — CloudFront 502 Troubleshooter

Command listings and safety checks moved verbatim from SKILL.md: the pre-flight gather-info script and the pre-flight safety checks.


---

## Pre-flight: distribution state and gather-info commands (moved from SKILL.md)

```bash
# 1. Distribution config (origins, behaviours, certificates, restrictions)
aws cloudfront get-distribution-config --id <id> --output json

# 2. Status and last-modified time
aws cloudfront get-distribution --id <id> --output json | \
  jq '.Distribution | {Status, DomainName, LastModifiedTime}'

# 3. CloudFront access logs (always us-east-1 log group)
aws logs filter-log-events \
  --log-group-name <cloudfront-log-group-arn> \
  --start-time $(date -d '-30 minutes' +%s)000 \
  --filter-pattern '"502" OR "504" OR "Error"' --output json

# 4. Reproduce from a viewer-like client (force fresh fetch)
curl -sv -H 'Cache-Control: no-cache' \
  https://<distribution-domain>/<failing-path> 2>&1 | \
  grep -E 'HTTP/|x-cache|x-amz-cf|x-edge'

# 5. Probe the origin directly, bypassing CloudFront
curl -sv --resolve <origin-host>:443:<origin-ip> \
  https://<origin-host>/<path> -H 'Host: <origin-host>' 2>&1
```


---

## Pre-flight safety checks (moved from SKILL.md)

- **MANDATORY CONFIRMATION GATE.** Before `update-distribution`,
  `create-invalidation`, or `delete-distribution`, emit and await
  operator approval.

- **Read-only first.** Every probe is read-only (`get-distribution`,
  `get-distribution-config`, `filter-log-events`, `describe-target-health`,
  `head-object`, `get-bucket-policy`, `openssl s_client`). Do not run
  state-changing operations as diagnostic probes.

- **`update-distribution`** moves Status to `InProgress` for 5-15 min;
  mixed POP behaviour during this window is expected.

- **`create-invalidation`** is billable after 1,000 paths/month. Use
  `/*` sparingly; target specific failing paths.

- **Lambda@Edge versioning.** A new function version does not affect the
  distribution until you update the
  `LambdaFunctionAssociations[].LambdaFunctionARN` to the new version.

- **Bucket policy edits** affect every consumer of the bucket. Tighten
  gradually; never deny-by-default without confirming no other CF
  distribution depends on the bucket.
