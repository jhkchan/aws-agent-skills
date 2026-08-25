# Diagnostic Commands (load on demand) — CloudFront Invalidation Operator

Command listings moved verbatim from SKILL.md: the live-account pre-flight capture and the pre-flight safety checks run before any remediation CLI.


---

## Live-account pre-flight (moved from SKILL.md)

**Live-account pre-flight (skip if offline plan audit):**
1. `aws cloudfront get-distribution --id <id>` — capture `Status`,
   `DomainName`, `LastModifiedTime`, `DistributionConfig.Enabled`,
   `DistributionConfig.Origins`, `ContinuousDeploymentPolicyId`
   (if present).
2. `aws cloudfront list-invalidations --distribution-id <id>
   --max-items 20` — capture recent invalidation history, including
   `Status`, `CreateTime`, `InvalidationBatch.Paths.Quantity`.
3. For continuous deployment: `aws cloudfront
   get-continuous-deployment-policy --id <policy-id>` — capture
   `StagingDistributionDnsName`, traffic percentage, and type
   (`TrafficConfig`).
4. For cost analysis: count the total paths invalidated this month
   across all distributions (`list-invalidations` per distribution,
   sum `Paths.Quantity`, subtract 1,000).


---

## Pre-flight safety checks (moved from SKILL.md)

- **MANDATORY CONFIRMATION GATE.** Before any `create-invalidation`
  call, emit: `CONFIRM: About to create a CloudFront invalidation on
  distribution <id> (domain <domain>). Paths: <pattern>. Estimated
  cost: <$X or "free tier">. Proceed? (yes/no)`. Do NOT execute until
  the operator confirms.

- **Capture pre-state for audit.** Before any invalidation:
  `aws cloudfront list-invalidations --distribution-id <id>
  --max-items 10 --output json > /tmp/<id>-inv-pre-$(date +%s).json`.

- **Verify distribution status.** `get-distribution --id <id>` —
  confirm `Status: Deployed` and `Enabled: true`. An invalidation on
  a Suspended or InProgress distribution may silently fail.

- **Verify origin health before invalidation.** If the origin is S3,
  verify the S3 bucket has the updated content. If the origin is a
  custom HTTP server, verify the server serves the correct response.
  Invalidating against a broken origin re-caches broken content.

- **Verify CallerReference uniqueness.** Check the last 20
  invalidations via `list-invalidations` to ensure the CallerReference
  has not been used before.

- **Prefer additive changes over destructive ones.** Versioned
  filenames (additive) are always safer than invalidation
  (destructive — clears cache). Only invalidate when versioned
  filenames are not possible (unversioned HTML, sensitive data
  removal, emergency content changes).
