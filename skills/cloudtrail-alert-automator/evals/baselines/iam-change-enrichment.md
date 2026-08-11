# Baseline (no-skill) response: iam-change-enrichment

This file captures what a generic assistant produces WITHOUT the
cloudtrail-alert-automator skill loaded.

---

To alert on IAM changes like AttachRolePolicy and DetachRolePolicy, you
can create an EventBridge rule that matches those event names from the
aws.iam source. Send the events to an SNS topic for notification.

You could write a Lambda function that gets triggered by the EventBridge
rule and uses the CloudTrail lookup-events API to get more context about
what the user was doing around that time. Then publish an enriched
message to SNS.

For deduplication, you might want to keep track of recent alerts somehow,
maybe in DynamoDB with a TTL. And for suppression, just check if the
caller is a known service role before sending the alert.

I don't have the exact CLI commands memorized but the general approach
is EventBridge rule → Lambda enrichment → SNS notification.
