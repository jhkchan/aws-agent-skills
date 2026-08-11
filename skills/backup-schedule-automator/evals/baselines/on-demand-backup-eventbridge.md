# Baseline (no-skill) response: on-demand-backup-eventbridge

This file captures what a generic assistant produces WITHOUT the
backup-schedule-automator skill loaded.

---

To trigger a backup after a CodePipeline deployment, you can set up an
EventBridge rule that watches for the pipeline success event. Then have
a Lambda function call start-backup-job for your DynamoDB table.

The EventBridge rule would look something like:

```
aws events put-rule --name backup-on-deploy --event-pattern '...'
```

The Lambda function would call:

```
aws backup start-backup-job --backup-vault-name on-demand-vault ...
```

Make sure to add the Lambda as a target with the right permissions.
