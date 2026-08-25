# Diagnostic Commands — shield-advanced-coverage-auditor

Moved verbatim from SKILL.md (progressive disclosure; load on demand). Sections keep their original headings.

---

## Live-account pre-flight commands (subscription gate)
**Live-account pre-flight (skip if doing offline config-doc audit):**
1. Verify the caller can run `shield:ListProtections` and
   `shield:DescribeDRTAccess` — most read-only auditor roles CAN, but
   `shield:AssociateDRTRole` (remediation) requires write access. Surface
   this BEFORE the operator approves a change.
2. Snapshot `aws shield list-protections` and
   `aws wafv2 list-web-acls --scope regional` (and `--scope cloudfront` for
   global ACLs) BEFORE any edit — protections and Web ACL associations are
   not versioned; a backup is the only rollback.
3. Confirm the region: Shield Advanced is a global service for CloudFront
   and Route 53, but ALB/NLB/CLB/EIP protections are regional. Audit each
   region independently — a clean us-east-1 does NOT imply clean eu-west-1.


## Pre-flight safety checks (run before any remediation CLI)

- **MANDATORY CONFIRMATION GATE.** Before any state-changing operation
  (`CreateSubscription`, `CreateProtection`, `DeleteProtection`,
  `AssociateDRTRole`, `AssociateDRTLogBucket`, `EnableProactiveEngagement`),
  the auditor MUST emit:
  `CONFIRM: About to <action> in account <account>. This affects
  <consequence>. Proceed? (yes/no)`
  Do NOT execute the CLI command until the operator confirms.

- **CreateSubscription is a financial commitment.** Explicitly state:
  "This starts a 1-year, non-cancellable, non-prorated commitment. The
  monthly fee applies regardless of the number of protected resources."
  Do NOT auto-execute — require explicit operator approval.

- **DeleteProtection drops coverage immediately.** There is no grace
  period. Confirm the resource is being decommissioned before removing a
  Protection. Capture the Protection ID for rollback:
  `aws shield describe-protection --protection-id <id>` BEFORE deletion.

- **AssociateDRTRole grants cross-service access.** The DRT role must have
  a trust policy allowing `service-role.shield.amazonaws.com` to assume it.
  Verify the role exists and has the correct trust policy BEFORE
  associating — an invalid role ARN makes DRT access non-functional.

- **Regional vs global scope.** ALB/NLB/CLB/EIP protections are regional.
  CloudFront/Route 53 are global. When remediating across regions, apply
  `CreateProtection` in EACH region independently — a protection in
  us-east-1 does NOT cover the same-named ALB in eu-west-1.

- Prefer additive changes (add a Protection, associate a health check) over
  destructive changes (delete a Protection) — additive changes are
  reversible and do not risk dropping coverage.

