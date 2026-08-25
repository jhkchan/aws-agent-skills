# Diagnostic Commands (load on demand) — CloudWatch Dashboards Operator

Pre-flight and diagnostic command listings moved verbatim from SKILL.md. Loaded on demand.

---

## Pre-flight safety checks (run before any remediation CLI) (moved from SKILL.md)

- **MANDATORY CONFIRMATION GATE.** Before any state-changing API
  (`put-dashboard`, `delete-dashboards`, `put-dashboard-sharing-config`,
  `oam create-sink`, `oam create-link`, `oam update-link`,
  `lambda add-permission`), emit: `CONFIRM: About to <operation> on
  <target> in account <account> region <region>. This will
  <consequence>. Proceed? (yes/no)`. Do NOT execute until the operator
  confirms.

- **Capture pre-state for dashboard updates.** Before PutDashboard on
  an existing dashboard: `aws cloudwatch get-dashboard --dashboard-name
  <name> --output json > /tmp/<name>-pre-$(date +%s).json`. This is
  critical because PutDashboard overwrites the entire body.

- **Verify OAM configuration for cross-account.** `aws oam list-sinks`
  to confirm a sink exists. `aws oam list-links` to confirm source
  accounts are linked. `aws oam get-link --identifier <id>` to verify
  `MetricLink: true`.

- **Verify Lambda permissions for custom widgets.** `aws lambda
  get-policy --function-name <fn>` — confirm
  `Principal: { Service: cloudwatch.amazonaws.com }` and `Action:
  lambda:InvokeFunction`.

- **Validate dashboard JSON before PutDashboard.** Use `jq` to parse
  the body: `jq . <body>.json > /dev/null`. If the JSON is invalid,
  PutDashboard returns a 400 error and may corrupt the existing
  dashboard.

- **Prefer additive updates over replacements.** When updating a
  dashboard, add new widgets rather than replacing the body with a
  minimal set. Removing widgets that other teams depend on causes
  silent visibility loss.
