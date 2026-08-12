# Baseline (no-skill) response: schedule-cron-syntax

---

Your EventBridge schedule rule is not firing. The state is DISABLED,
which means EventBridge turned it off. The cron expression
`cron(0 9 * * *)` looks like a standard cron expression. Try
re-enabling the rule with `aws events enable-rule`. If it gets disabled
again, check the cron syntax. EventBridge might need a slightly
different format.
