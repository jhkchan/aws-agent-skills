# Diagnostic and pre-flight commands — network-firewall-rule-auditor

Pre-flight safety gates and command listings moved verbatim from SKILL.md (load on demand).

## Pre-flight safety checks (run before any remediation CLI)

- **MANDATORY CONFIRMATION GATE.** Before any state-changing operation
  (`update-firewall-policy`, `update-rule-group`,
  `associate-tls-inspection-config`, `update-logging-configuration`,
  `replace-route`), emit:
  `CONFIRM: About to <action> on firewall <name> / policy <arn>. This
  affects <consequence> and <N> attached firewall(s). Proceed? (yes/no)`
  Do NOT execute until the operator confirms.
- **Blast-radius enumeration.** Before editing a policy, run:
  `aws network-firewall list-firewalls --firewall-policy-arn <arn>` and
  report the count. A shared policy change affects every attached firewall.
- **Backup the current policy:**
  `aws network-firewall describe-firewall-policy --firewall-policy-arn <arn> --output json > /tmp/<name>-policy-backup-$(date +%s).json`
  BEFORE any modification. Policy changes are not versioned — there is no
  automatic rollback.
- **Re-fetch `UpdateToken` immediately before each mutation.** Do not reuse a
  token from a prior call.
- **Route-table changes affect live traffic.** `replace-route` on a production
  route table can cause instantaneous traffic disruption. Always test in a
  staging VPC first and apply during a maintenance window.
- For PERMISSIVE_RULE findings (wildcard pass, fragment bypass), treat as
  high-priority — the firewall is actively configured to allow traffic that
  should be inspected or blocked. Remediate before the next change window.
- Prefer additive changes (add a `drop` rule, change a default action to
  include `forward_to_sfe`) over destructive changes (remove a `pass` rule
  that may be load-bearing for a workload you did not anticipate).
