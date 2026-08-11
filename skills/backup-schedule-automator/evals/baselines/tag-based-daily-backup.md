# Baseline (no-skill) response: tag-based-daily-backup

This file captures what a generic assistant produces WITHOUT the
backup-schedule-automator skill loaded — the contrast that proves
the skill adds structure (deterministic VERDICT, lifecycle tiering,
tag-based selection, cross-region copy, restore testing).

---

For a daily backup of DynamoDB and EBS resources, you can create a
backup plan with a daily schedule and tag-based selection. Use the
backup-plan=daily-prod tag to select resources.

Create a backup plan with something like:

```
aws backup create-backup-plan --backup-plan '{"BackupPlanName":"daily-prod","Rules":[...]}'
```

Set the retention to 30 days. You might also want to copy backups to
another region for DR.

Make sure the IAM role has permissions for DynamoDB and EBS backups.
