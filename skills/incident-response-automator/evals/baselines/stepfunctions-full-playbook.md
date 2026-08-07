# Baseline (no-skill) response: stepfunctions-full-playbook

This file captures what a generic assistant produces WITHOUT the
incident-response-automator skill loaded.

---

For a full incident response playbook, you can use Step Functions to
orchestrate multiple Lambda functions. The state machine would look
something like:

1. Receive finding from EventBridge
2. Quarantine the EC2 instance (Lambda)
3. Snapshot the volumes (Lambda)
4. Send a notification (Lambda)
5. Wait for a human to review
6. Recover or close

You can use the Step Functions console to build this visually, or write
the Amazon States Language JSON by hand. Make sure to add error handling
for each step.
