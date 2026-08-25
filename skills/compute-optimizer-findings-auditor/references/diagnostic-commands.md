# Diagnostic Commands (load on demand) — Compute Optimizer Findings Auditor

Live-account pre-flight checks and pre-remediation safety checks, moved verbatim from SKILL.md.


---

## Live-account pre-flight checks (enrollment and data gate) (moved from SKILL.md)

**Live-account pre-flight checks (skip if doing offline finding-doc audit):**
1. Verify enrollment: `aws compute-optimizer get-enrollment-status`. If
   `status: Inactive`, the account is NOT enrolled — no findings exist
   regardless of resource count. Output `NOT_OPTIMIZED` with reason
   "enrollment inactive."
2. Paginate findings: EC2/EBS/Lambda recommendation APIs return up to 1,000
   items per page. Use `--next-token` from the prior response to page through
   all resources; iterating only the first page silently skips the long tail.
3. Cross-check CloudTrail for `compute-optimizer:Get*Recommendations` calls —
   a recommendation export may have been run days ago and the findings are
   stale. Always check `lastRefreshTimestamp` on each finding.

## Pre-flight safety checks (run before any remediation CLI) (moved from SKILL.md)

- **MANDATORY CONFIRMATION GATE.** Before any instance stop, type change,
  volume modification, or Lambda update, the auditor MUST emit:
  `CONFIRM: About to <action> on <resource-id> in account <account>. This
  will cause <consequence>. Proceed? (yes/no)`
  Do NOT execute the CLI command until the operator confirms.

- **Snapshot EC2 before right-sizing.** Capture the current state:
  `aws ec2 create-image --instance-id <id> --name "pre-rightsize-$(date +%s)"`
  before stopping and changing instance type. This provides a rollback path
  if the new type cannot handle the workload.

- **For ASG right-sizing:** update the launch template version, then trigger
  an instance refresh: `aws autoscaling start-instance-refresh`. Monitor
  the rollout — a failed refresh should be rolled back to the previous
  template version.

- **For EBS volume type changes:** `aws ec2 modify-volume --volume-id <id>
  --volume-type gp3` is non-disruptive (the volume stays online), but
  performance may degrade during the migration window. Flag this in the
  confirmation gate.

- **For Lambda memory changes:** `aws lambda update-function-configuration
  --function-name <name> --memory-size <mb>` takes effect immediately on
  the next invocation. Test with a small percentage of traffic first (use
  alias routing) before applying to all invocations.

- **Verify CWAgent is installed** before acting on any EC2 finding. If
  Memory metrics are absent, install CWAgent first, wait 30 days, then
  re-evaluate. Right-sizing without memory data is guessing.

- Prefer the recommendation option with `performanceRisk` ≤ 2, even if it
  has slightly lower savings. The cost of a performance regression
  (customer impact, rollback effort) exceeds the marginal savings of a
  riskier option.
