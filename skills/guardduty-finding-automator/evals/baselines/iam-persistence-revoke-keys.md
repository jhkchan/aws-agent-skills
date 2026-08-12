# Baseline (no-skill) response: iam-persistence-revoke-keys

This file captures what a generic assistant produces WITHOUT the
guardduty-finding-automator skill loaded — the contrast that proves
the skill adds structure (deterministic VERDICT, severity-based IAM
key revocation with last-used check, Security Hub ASFF ingestion,
CloudTrail TTP correlation, finding ID deduplication).

---

For a GuardDuty finding about a new IAM access key being created
suspiciously, you should deactivate the key. You can use a Lambda
triggered by EventBridge to call iam update_access_key and set the
status to Inactive.

You'll need to figure out which key was created and revoke just that
one. The finding should have the access key ID in it.

You might also want to send a notification to your security team via
SNS. And maybe log it to Security Hub.

I'm not sure about the exact EventBridge pattern for this finding
type. You might need to filter on the finding type in the event detail.
