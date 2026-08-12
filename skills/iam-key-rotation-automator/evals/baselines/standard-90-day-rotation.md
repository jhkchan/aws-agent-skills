# Baseline (no-skill) response: standard-90-day-rotation

This file captures what a generic assistant produces WITHOUT the
iam-key-rotation-automator skill loaded — the contrast that proves
the skill adds structure (deterministic VERDICT, overlap window
design, access advisor integration, exception handling).

---

The access key is 91 days old, so you should rotate it. You can
create a new key with `aws iam create-access-key`, then update your
application to use the new key. After that, deactivate the old key
and eventually delete it.

Make sure the new key works before deleting the old one. You can use
`aws sts get-caller-identity` to test the new key.

Set up a CloudWatch alarm or EventBridge rule to check key ages
periodically.
