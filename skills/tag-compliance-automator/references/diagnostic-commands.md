# Diagnostic Commands — Tag Compliance Automator

> Moved verbatim from SKILL.md for progressive disclosure (agentskills.io). Load on demand.

## Pre-flight safety checks

- **MANDATORY CONFIRMATION GATE.** Before any state-changing operation,
  emit: `CONFIRM: About to <action> for tag compliance in <target>.
  This affects <consequence>. Proceed? (yes/no)`
- **Back up the current TagPolicy** before modifying:
  `aws organizations describe-policy --policy-id p-xxxxxxx > /tmp/tag-policy-backup.json`
- **Before flipping from advisory to enforced**, dry-run by listing
  NON_COMPLIANT resources via Config first.
- **For StackSet deployment**, verify admin and execution roles exist in
  every target account.
