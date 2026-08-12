# Baseline (no-skill) response: ec2-ssh-bruteforce-auto-isolate

This file captures what a generic assistant produces WITHOUT the
guardduty-finding-automator skill loaded — the contrast that proves
the skill adds structure (deterministic VERDICT, severity-based routing,
safety gates, finding ID deduplication, expert GuardDuty+EventBridge
knowledge).

---

You can set up an EventBridge rule to trigger a Lambda function when
GuardDuty detects an SSH brute force finding. The Lambda can isolate
the EC2 instance by changing its security group.

Create an EventBridge rule with the GuardDuty event pattern and add
the Lambda as a target. The Lambda should call modify_network_interface
to swap the security group to an isolation one.

You'll need an IAM role for the Lambda with EC2 permissions.

Something like:

```
aws events put-rule --name guardduty-ssh --event-pattern '{"source":["aws.guardduty"]}'
aws lambda create-function ...
```

I don't remember the exact severity filtering syntax for EventBridge.
You might need to look it up.
