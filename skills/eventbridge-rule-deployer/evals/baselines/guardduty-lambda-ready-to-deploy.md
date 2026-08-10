# Baseline (no-skill) response: guardduty-lambda-ready-to-deploy

This file captures what a generic assistant produces WITHOUT the
eventbridge-rule-deployer skill loaded — the contrast that proves
the skill adds structure (deterministic VERDICT, working CLI plan,
DLQ/retry, pre-flight checklist, expert EventBridge knowledge).

---

To trigger a Lambda on GuardDuty findings, create an EventBridge
rule on the default bus. The event source is `aws.guardduty` and
the detail-type is `GuardDuty Finding`. Filter on severity if you
only want high-severity ones.

Then add the Lambda as a target. The CLI looks something like:

```
aws events put-rule --name guardduty --event-pattern '...'
aws events put-targets --rule guardduty --targets '[...]'
```

Make sure the Lambda has permission to be invoked by EventBridge.
You may also want to set up a DLQ in case the Lambda fails.
