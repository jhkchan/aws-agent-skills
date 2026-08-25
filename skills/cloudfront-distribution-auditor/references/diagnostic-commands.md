# Diagnostic Commands (load on demand) — CloudFront Distribution Auditor

Safety checks moved verbatim from SKILL.md: the pre-flight safety checks run before any remediation CLI.


---

## Pre-flight safety checks (moved from SKILL.md)

- **MANDATORY CONFIRMATION GATE.** Before any state-changing operation
  (update-distribution, associate-web-acl, create-origin-access-control),
  the auditor MUST emit:
  `CONFIRM: About to <action> on distribution <id> in account <account>.
  This affects <consequence>. Proceed? (yes/no)`
  Do NOT execute the CLI command until the operator confirms. Distribution
  changes propagate globally — a misconfiguration affects every edge location.
- Confirm the distribution exists and is accessible:
  `aws cloudfront get-distribution-config --id <id> --profile <p>` — fail
  closed (skip remediation) if it returns an error.
- Capture the current distribution config for rollback:
  `aws cloudfront get-distribution-config --id <id> --output json >
  /tmp/<id>-config-backup-$(date +%s).json` BEFORE any modification.
  Distribution configs are versioned via ETag, but there is no automatic
  rollback — the ETag is required for the update call.
- Before changing `MinimumProtocolVersion`, verify that no legacy clients
  require TLS 1.0/1.1. Some embedded devices, legacy POS terminals, or
  older Java runtimes cannot negotiate TLS 1.2+. Coordinate with application
  owners before enforcing TLSv1.2_2021.
- Before creating OAC and updating the origin, prepare the S3 bucket policy
  update simultaneously. OAC without the bucket policy update breaks all
  object access; the bucket policy without OAC is inert.
- Before associating a Web ACL, verify it exists in us-east-1 with
  `CLOUDFRONT` scope: `aws wafv2 list-web-acls --scope CLOUDFRONT --region
  us-east-1`. A Web ACL in any other region cannot be associated.
- **ETag requirement.** Every `update-distribution` call requires the
  current `ETag` from `get-distribution-config`. A stale ETag (config
  changed between read and update) causes `PreconditionFailedException`.
  Always re-fetch the ETag immediately before the update call.
- **Propagation delay.** Distribution changes take 5-60 minutes to propagate
  globally after `update-distribution` returns `DeploymentStatus: Deployed`.
  Do not treat the API response as the effective state — verify via
  `get-distribution` `Status: Deployed` before declaring remediation complete.
