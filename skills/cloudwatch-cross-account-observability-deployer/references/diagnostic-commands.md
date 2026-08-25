# Diagnostic Commands (load on demand) — CloudWatch Cross-Account Observability Deployer

Pre-flight and diagnostic command listings moved verbatim from SKILL.md. Loaded on demand.

---

## Pre-flight safety checks (run before any OAM CLI) (moved from SKILL.md)

- **Confirm OAM is available in the Region:** `aws oam list-sinks
  --region <r>` (no error = available).
- **Confirm the monitoring account principal:** the IAM role must
  include a policy with `oam:CreateSink`, `oam:PutSinkPolicy`.
- **Confirm each source account principal:** in each source
  account, the IAM role must include `oam:CreateLink` on the sink
  ARN.
- **Confirm the sink policy resource principals:** `aws oam
  get-sink-policy --sink-identifier <arn>` MUST list each source
  account principal OR the org ID.
- **Confirm Application Signals is enabled in each source** (if
  cross-account Application Signals desired): `aws
  application-signals list-services` returns the workload.
- **Confirm Managed Grafana / AMP workspaces exist** (if
  integration desired): `aws grafana list-workspaces`,
  `aws amp list-workspaces`.
- **Confirm CloudWatch Logs groups exist before referencing in
  the link filter:** `aws logs describe-log-groups`.
