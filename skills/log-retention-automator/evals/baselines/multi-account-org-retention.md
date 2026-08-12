# Baseline (no-skill) response: multi-account-org-retention

This file captures what a generic assistant produces WITHOUT the
log-retention-automator skill loaded — the contrast that proves
the skill adds structure (deterministic VERDICT, tier validation,
EventBridge automation, Firehose archival, cost estimation, expert
CloudWatch Logs knowledge).

---

For a multi-account setup, you can use CloudFormation StackSets
to deploy the retention Lambda and EventBridge rule to all 45
accounts. Use SERVICE_MANAGED so it auto-deploys to new accounts.

```
aws cloudformation create-stack-set --stack-set-name log-retention ...
aws cloudformation create-stack-instances --deployment-targets ...
```

You'll need an IAM role that the Lambda can assume in each
account. The management account can run a sweep Lambda that
checks all accounts for Never Expire groups.

Make sure each account has the right permissions configured.
