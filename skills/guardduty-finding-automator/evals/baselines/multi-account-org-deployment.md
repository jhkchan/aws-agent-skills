# Baseline (no-skill) response: multi-account-org-deployment

This file captures what a generic assistant produces WITHOUT the
guardduty-finding-automator skill loaded — the contrast that proves
the skill adds structure (deterministic VERDICT, Organizations delegated
admin setup, cross-account EventBridge forwarding, StackSet deployment,
per-Region designation, auto-enable for new accounts).

---

For multi-account GuardDuty, you should set up a delegated administrator
account. Use enable-organization-admin-account to designate the admin
account, then member accounts will be managed from there.

You can deploy your Lambda remediation function to all accounts using
CloudFormation StackSets. Each account needs its own EventBridge rule
to forward findings to the admin account.

I think the command is something like:

```
aws guardduty enable-organization-admin-account --admin-account-id 111111111111
```

For the cross-account forwarding, you'd need to set up an EventBridge
rule in each member account that sends to the admin's event bus. You'll
need IAM roles for cross-account event bus access.

I'm not sure about the exact setup for all Regions — you might need
to repeat the delegated admin setup in each Region.
