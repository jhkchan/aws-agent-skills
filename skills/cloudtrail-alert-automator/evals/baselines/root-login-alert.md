# Baseline (no-skill) response: root-login-alert

This file captures what a generic assistant produces WITHOUT the
cloudtrail-alert-automator skill loaded — the contrast that proves the
skill adds structure (deterministic VERDICT, EventBridge pattern,
enrichment Lambda, severity routing, suppression hygiene).

---

You can set up a CloudTrail alert for root login by creating an
EventBridge rule. The event pattern would look for ConsoleLogin events
where the user is root. Then send it to an SNS topic to get notified.

Something like:

```
aws events put-rule --name root-login --event-pattern '{"source":["aws.signin"],"detail":{"eventName":["ConsoleLogin"]}}'
```

Then add an SNS target. You might also want to filter for successful
logins only but I'm not sure what the exact field is.

You should also set up a Lambda function to enrich the alert with more
context, but the basic EventBridge + SNS setup should work for starters.
