# Baseline (no-skill) response: multi-account-org-trail

This file captures what a generic assistant produces WITHOUT the
cloudtrail-alert-automator skill loaded.

---

For multi-account CloudTrail alerting with an Organizations trail, you
can set up EventBridge rules in the management account. Since the org
trail sends all events to the management account, you can filter on the
accountId field to route alerts per member account.

Create rules in the management account for root login, IAM changes, and
trail tampering. Use SNS topics and have each member account subscribe
their notification endpoints.

You might need cross-account permissions for SNS subscriptions. The
member accounts would need to subscribe their Lambda functions or email
addresses to the management account's SNS topics.

For per-account suppression, each account would maintain its own list
of service roles to suppress in the Lambda function configuration.
