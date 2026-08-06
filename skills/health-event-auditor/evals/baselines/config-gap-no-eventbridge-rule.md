# Baseline (no-skill) response: config-gap-no-eventbridge-rule

This file captures what a generic assistant produces WITHOUT the
health-event-auditor skill loaded.

---

You don't have an EventBridge rule set up for AWS Health events. This
means even though Health events are being delivered to your default
event bus, nothing is consuming them — so you won't get any
notifications when something goes wrong.

You should create an EventBridge rule with source `aws.health` and add
a target like an SNS topic or Lambda function.
