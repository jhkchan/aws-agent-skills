# Baseline (no-skill) response: eventbridge-pattern-gap

This file captures what a generic assistant produces WITHOUT the
incident-response-automator skill loaded.

---

This EventBridge rule looks good. It matches all GuardDuty findings and
routes them to the Step Functions state machine. The kill-switch and
manual approval gate in the state machine provide the necessary safety
controls. Since the workflow has idempotency checks and scoped IAM
roles, it should be safe to deploy.
