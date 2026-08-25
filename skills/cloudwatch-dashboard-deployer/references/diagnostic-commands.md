# Diagnostic Commands (load on demand) — CloudWatch Dashboard Deployer

Pre-flight and diagnostic command listings moved verbatim from SKILL.md. Loaded on demand.

---

## Pre-flight safety checks (run before any provisioning CLI) (moved from SKILL.md)

- **MANDATORY CONFIRMATION GATE.** Before any state-changing operation
  (`put-dashboard`, `delete-dashboards`), the operator MUST emit:
  `CONFIRM: About to <action> dashboard <name> in account <account>
  region <region>. This affects <consequence>. Proceed? (yes/no)`. Do
  NOT execute the CLI command until the operator confirms.

- **PutDashboard overwrites the entire dashboard body.** Always snapshot
  before modification:
  `aws cloudwatch get-dashboard --dashboard-name <name> --output json >
  /tmp/<name>-backup-$(date +%s).json`.

- For cross-account dashboards, verify the sharing role exists in EACH
  source account before deploying. A missing role is the #1 cause of
  empty cross-account widgets.

- For dashboards with log insights widgets, test the query in the
  CloudWatch Logs Insights console first to estimate render time.
  Queries on large log groups (>100 GB ingested) can take 30+ seconds
  and cause dashboard load timeouts.

- Prefer additive changes (add widgets, add dashboard variables) over
  destructive changes (replace entire dashboard body) — additive
  changes are reversible and do not risk removing existing operational
  views.

- For dashboards shared via snapshot, ensure the S3 bucket lifecycle
  policy is configured — snapshots accumulate and incur storage costs
  if not cleaned up.
