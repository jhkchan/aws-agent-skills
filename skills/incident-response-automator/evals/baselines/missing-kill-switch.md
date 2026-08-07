# Baseline (no-skill) response: missing-kill-switch

This file captures what a generic assistant produces WITHOUT the
incident-response-automator skill loaded.

---

This workflow looks functional. It triggers on high-severity GuardDuty
findings and automatically contains the threat by quarantining the EC2
instance, snapshotting the volumes, and terminating it. The IAM role
grants ec2:* which is broad but covers all the actions the Lambda needs.
The workflow is fully automated — no human intervention required, which
is good for reducing response time.

For production use, you may want to consider adding some error handling
or retry logic to the Lambda function.
