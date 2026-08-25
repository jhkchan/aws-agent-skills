# Diagnostic Commands (load on demand) — CloudFront Cost Optimizer

Command listings and safety checks moved verbatim from SKILL.md: the required data-source pulls and the pre-flight safety checks.


---

## Pre-flight: required data sources (moved from SKILL.md)

```bash
# 1. Pull the full distribution config (origins, behaviors, price class)
DIST_ID=E1ABC23DEF456G

aws cloudfront get-distribution-config --id $DIST_ID --output json \
  > dist-config.json

# 2. Pull 14-30 day CloudFront metrics
START=$(date -u -d '-30 days' +%FT%TZ)
END=$(date -u +%FT%TZ)

aws cloudwatch get-metric-statistics \
  --namespace AWS/CloudFront \
  --metric-name CacheHitRate \
  --dimensions Name=DistributionId,Value=$DIST_ID \
  --start-time $START --end-time $END \
  --period 86400 --statistics Average,Minimum,Maximum \
  --output json > cache-hit-rate.json

aws cloudwatch get-metric-statistics \
  --namespace AWS/CloudFront \
  --metric-name Requests \
  --dimensions Name=DistributionId,Value=$DIST_ID \
  --start-time $START --end-time $END \
  --period 86400 --statistics Sum \
  --output json > requests.json

aws cloudwatch get-metric-statistics \
  --namespace AWS/CloudFront \
  --metric-name BytesDownloaded \
  --dimensions Name=DistributionId,Value=$DIST_ID \
  --start-time $START --end-time $END \
  --period 86400 --statistics Sum \
  --output json > bytes.json

# 3. (Optional) pull Cost Explorer line items for CloudFront
aws ce get-cost-and-usage \
  --time-period Start=$(date -u -d '-30 days' +%F),End=$(date -u +%F) \
  --filter '{"Dimensions":{"Key":"SERVICE","Values":["Amazon CloudFront"]}}' \
  --granularity MONTHLY \
  --metrics "BlendedCost" "UsageQuantity" \
  --group-by Type=DIMENSION,Key=USAGE_TYPE \
  --output json > ce-cloudfront.json

# 4. (Optional) pull viewer geography from CloudFront access logs
# Requires logging enabled on the distribution. The c-edge-location
# column in the standard log format is the authoritative source of
# viewer geography.
```


---

## Pre-flight safety checks (moved from SKILL.md)

- **MANDATORY CONFIRMATION GATE.** Before any state-changing
  operation (`update-distribution`, `create-cache-policy`,
  `delete-protection`, `create-savings-plan`), emit and await
  operator approval. Do NOT execute the CLI until the operator
  confirms.

- **Snapshot before optimization.** Capture the current config:
  `aws cloudfront get-distribution-config --id <id> --output json
  > backup-pre-optimization-$(date +%s).json`. This provides a
  rollback path if the new config produces cache-hit drops or 5xx.

- **One dimension per deploy.** CloudFront distributions are
  eventually-consistent; each update takes 5-15 minutes to deploy.
  Stacking multiple dimension changes in a single update obscures
  which change produced any observed impact. Deploy dimensions
  sequentially with 24-48h monitoring between each.

- **Verify distribution Status returns to Deployed.** After each
  update:
  `aws cloudfront get-distribution --id <id> --query
  'Distribution.Status'`. Status transitions: Deployed → InProgress
  → Deployed. Do not issue the next update until Status is Deployed.

- **Bulk-operation safety limit.** Optimization across a fleet of
  distributions MUST follow this algorithm:
  1. Sort flagged distributions by estimated savings (largest first).
  2. Slice into batches of at most 3 distributions.
  3. For each batch: emit per-distribution MIGRATION_STEPS, then a
     single CONFIRM for the batch.
  4. After the operator confirms and the CLI runs, re-query with
     `get-distribution` and verify Status == Deployed before
     emitting the NEXT batch.
  5. Abort the sweep if any distribution shows 5xx increase or
     CacheHitRate drop > 10% post-change.
  The skill MUST NOT emit remediation CLI for more than 3
  distributions in a single output block.

- **Cache invalidation is a separate cost.** If the optimization
  changes the cache policy, existing cache entries may be stale.
  Invalidation via `aws cloudfront create-invalidation` costs
  $0.005 per path after the first 1,000 paths/month free tier.
  Surface invalidation cost in the savings estimate.

- **Lambda@Edge replica deletion is slow.** Disassociating a
  Lambda@Edge function from a distribution does not immediately
  delete the replicas in edge regions. Replicas take 1-24 hours to
  delete. During that window, CloudWatch logs continue to show
  invocations from residual replicas. Surface this in the
  verification step.
