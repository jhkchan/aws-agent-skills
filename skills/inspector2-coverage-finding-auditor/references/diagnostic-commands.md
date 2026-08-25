# Inspector2 Coverage + Finding Auditor — diagnostic & pre-flight commands (moved verbatim from SKILL.md)

> Progressive-disclosure split: this content was moved verbatim from SKILL.md; nothing was rewritten.

## Step 0 — contradictory-data branches and account-level status branches

**Contradictory data handling (explicit decision branches):**

| Data Contradiction | Classification | Reason |
|---|---|---|
| Finding references a resource with no coverage entry | **MEDIUM** | Data inconsistent — cannot verify coverage |
| Coverage says ACTIVE but SSM PingStatus is offline | **HIGH** (prod) / **MEDIUM** (standard) | SSM offline overrides coverage status |
| Finding says OPEN but `lastScannedAt` is more recent than `findingUpdatedAt` | **MEDIUM** | Finding may be stale — next scan will reconcile |
| Input provides scanOnPush for ECR but no `lastScannedAt` | **MEDIUM** | Never scanned despite scanOnPush — cannot confirm ACTIVE |
| Multiple coverage records for the same resource with different statuses | Use the WORST status | Conservative — the worse record reflects a real gap |

Check the Inspector2 account-level batch status
(`aws inspector2 batch-get-account-status`). For each resource type:

- **EC2 scanning** `status: ENABLED` → proceed to Step 1 coverage check.
- **EC2 scanning** `status: DISABLED` → ALL EC2 instances in this region are
  uncovered. If ANY EC2 instance exists in the region, this is a blanket
  coverage gap (Step 2).
- **ECR scanning** `status: ENABLED` → ECR scanning is on, but per-repo
  `scanOnPush` still matters (Step 1).
- **ECR scanning** `status: DISABLED` → ALL ECR images are uncovered.
- **LAMBDA scanning** `status: ENABLED` → Lambda standard scanning on.
  Check for code-scanning opt-in separately.
- **LAMBDA scanning** `status: DISABLED` → ALL Lambda functions uncovered.
- **LAMBDA_CODE scanning** `status: ENABLED` → deep code scanning on
  (catches dependency-graph vulnerabilities beyond runtime).

## Pre-flight safety checks — CLI listing (from SKILL.md)

- Confirm the resource exists and is in the expected account/region:
  `aws inspector2 list-coverage --filter-criteria <criteria>` — fail
  closed (skip remediation) if the resource is not in the coverage list.
- Before suppressing a finding (to avoid false suppression), capture the
  full finding detail:
  `aws inspector2 batch-get-finding-details --finding-ids <id> > /tmp/<id>-backup-$(date +%s).json`.
  Suppression is reversible, but the original finding detail should be
  retained for audit trails.
- Before patching an EC2 instance (to remediate a CVE), verify the
  patch is available in the SSM Patch Baseline:
  `aws ssm describe-patch-baselines` and check the instance's patch
  compliance state. Applying a patch not in the baseline can break the
  workload.
- For ECR remediation (rebuilding an image with patched base layers),
  confirm the new base image digest BEFORE pushing. A typo in the base
  image tag can introduce a DIFFERENT vulnerability. Use
  `aws ecr describe-images` to verify the base layer.
- For internet-reachable CRITICAL findings, treat as incident response:
  contain FIRST (restrict the security group or detach the internet
  gateway), then patch. Patching takes time; containment is seconds.
  Capture forensic state (CloudTrail, VPC Flow Logs) after containment.
