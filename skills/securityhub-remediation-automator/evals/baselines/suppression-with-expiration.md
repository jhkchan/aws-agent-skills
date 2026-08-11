# Baseline (no-skill) response: suppression-with-expiration

This file captures what a generic assistant produces WITHOUT the
securityhub-remediation-automator skill loaded.

---

To suppress the SQS finding, you can use the Security Hub console to
archive it or use the API to update the workflow status to SUPPRESSED.
Add a note explaining why you're suppressing it.

```
aws securityhub batch-update-findings --finding-identifiers ... --workflow ...
```

Make sure to set a reminder to review this suppression later, maybe in
a calendar or a ticket. You don't want to forget about it.
