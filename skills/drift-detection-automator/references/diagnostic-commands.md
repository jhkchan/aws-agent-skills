# Diagnostic Commands (load on demand) — Drift Detection Automator

Pre-flight safety checks moved verbatim from SKILL.md.


---

## Pre-flight safety checks (moved from SKILL.md)


- **MANDATORY CONFIRMATION GATE.** Before state-changing operations:
  `CONFIRM: About to <action> for stack <stack> in account <account>.
  Proceed? (yes/no)`

- **Verify the stack exists and is stable** before scheduling:
  `describe-stacks --stack-name <name> --query 'Stacks[0].StackStatus'`

- **For production, verify the approval SNS topic has confirmed
  subscriptions.** Unconfirmed means `aws:approve` blocks indefinitely.

- **Test the remediation SSM document in non-production.** Create
  deliberate drift, run the document, verify the stack returns to
  `IN_SYNC`.

- **For StackSets, verify `auto-deployment`** so new accounts receive
  the drift detection pipeline automatically.