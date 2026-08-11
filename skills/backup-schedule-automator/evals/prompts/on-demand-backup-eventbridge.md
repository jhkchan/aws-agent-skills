# Eval prompt: on-demand-backup-eventbridge

Design an on-demand backup trigger using EventBridge and Lambda for the
following scenario. Emit the standard BACKUP block including the
EventBridge rule and Lambda function template.

Design reference: on-demand-backup-eventbridge
Account: 111111111111
Region: us-east-1

Trigger: CodePipeline pipeline execution state change to SUCCEEDED
Pipeline name: prod-orders-pipeline
Target resource: arn:aws:dynamodb:us-east-1:111111111111:table/prod-orders-table
Backup vault: on-demand-vault
Retention: 7 days (DeleteAfterDays=7, no cold storage)
DLQ: arn:aws:sqs:us-east-1:111111111111:backup-trigger-dlq
IAM role: arn:aws:iam::111111111111:role/AWSBackupDefaultServiceRole
