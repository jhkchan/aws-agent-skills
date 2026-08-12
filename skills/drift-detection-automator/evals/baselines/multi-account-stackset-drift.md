# Baseline (no-skill) response: multi-account-stackset-drift

This file captures what a generic assistant produces WITHOUT the
drift-detection-automator skill loaded — the contrast that proves
the skill adds structure (deterministic VERDICT, StackSet deployment
pattern, per-instance iteration, Config Aggregator cross-account).

---

For multi-account drift detection, you can use CloudFormation StackSets
to deploy your drift detection Lambda to all accounts. Then use a
Config Aggregator to get cross-account visibility.

The StackSet would deploy the EventBridge rule and Lambda to each
account in the OU. Each Lambda detects drift on the local stacks and
sends results to the central SNS topic.

I think the command is something like:

```
aws cloudformation create-stack-set --stack-set-name drift-detection ...
aws cloudformation create-stack-instances --deployment-targets ...
```

For the Config Aggregator, you set it up in the delegated admin account
and it pulls Config data from all member accounts.

You'd also need to iterate stack instances for per-stack drift detection.
I'm not sure about the exact API for that — maybe list-stack-instances?
