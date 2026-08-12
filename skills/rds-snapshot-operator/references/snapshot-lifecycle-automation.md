# RDS Snapshot Lifecycle Automation Reference

Load this reference when implementing automated snapshot lifecycle
policies, cross-region DR pipelines, or snapshot cleanup Lambda
functions.

## Automation options comparison

| Tool | Best for | Cross-region | Cross-account | Retention policy | Cost |
|---|---|---|---|---|---|
| **RDS automated backups** | PITR window (1-35 days) | No (per-region) | No | Per-instance setting | $0.095/GB-month |
| **DLM (Data Lifecycle Manager)** | EBS-based snapshots, scheduled creation | Yes (cross-region copy rule) | No | Tag-based policies | Free (DLM) + snapshot storage |
| **AWS Backup** | Centralized governance, multi-service | Yes (copy rule) | Yes (backup vault) | Backup plan with lifecycle rules | Free (AWS Backup) + snapshot storage |
| **Custom Lambda + EventBridge** | Custom logic, tag-based filtering, compliance holds | Yes (copy-db-snapshot) | Yes (share-db-snapshot) | Fully customizable | Lambda invocations + snapshot storage |

## Lambda lifecycle cleanup function

```python
import boto3
import datetime
from datetime import timezone, timedelta

rds = boto3.client('rds')
RETENTION_DAYS = 30
SKIP_TAG_KEY = 'DoNotDelete'
SKIP_TAG_VALUE = 'true'

def lambda_handler(event, context):
    cutoff = datetime.datetime.now(timezone.utc) - timedelta(days=RETENTION_DAYS)
    deleted = []
    skipped = []
    errors = []

    # Paginate through all manual snapshots
    paginator = rds.get_paginator('describe_db_snapshots')
    for page in paginator.paginate(SnapshotType='manual'):
        for snap in page.get('DBSnapshots', []):
            snap_id = snap['DBSnapshotIdentifier']
            created = snap.get('SnapshotCreateTime')

            if not created or created > cutoff:
                continue  # Not old enough

            # Check for compliance-hold tag
            tags = rds.list_tags_for_resource(
                ResourceName=snap['DBSnapshotArn']
            ).get('TagList', [])

            skip = any(
                t['Key'] == SKIP_TAG_KEY and t['Value'] == SKIP_TAG_VALUE
                for t in tags
            )

            if skip:
                skipped.append(snap_id)
                continue

            # Delete the snapshot
            try:
                rds.delete_db_snapshot(DBSnapshotIdentifier=snap_id)
                deleted.append(snap_id)
            except Exception as e:
                errors.append(f"{snap_id}: {str(e)}")

    # Also handle Aurora cluster snapshots
    for page in paginator.paginate(SnapshotType='manual'):
        for snap in page.get('DBClusterSnapshots', []):
            snap_id = snap['DBClusterSnapshotIdentifier']
            created = snap.get('SnapshotCreateTime')

            if not created or created > cutoff:
                continue

            tags = rds.list_tags_for_resource(
                ResourceName=snap['DBClusterSnapshotArn']
            ).get('TagList', [])

            skip = any(
                t['Key'] == SKIP_TAG_KEY and t['Value'] == SKIP_TAG_VALUE
                for t in tags
            )

            if skip:
                skipped.append(snap_id)
                continue

            try:
                rds.delete_db_cluster_snapshot(
                    DBClusterSnapshotIdentifier=snap_id
                )
                deleted.append(snap_id)
            except Exception as e:
                errors.append(f"{snap_id}: {str(e)}")

    return {
        'deleted': deleted,
        'skipped': skipped,
        'errors': errors,
        'cutoff_date': cutoff.isoformat()
    }
```

## EventBridge schedule rule

```bash
# Create the EventBridge rule (daily at 02:00 UTC)
aws events put-rule \
  --name rds-snapshot-cleanup-daily \
  --schedule-expression "cron(0 2 * * ? *)"

# Attach the Lambda as target
aws events put-targets \
  --rule rds-snapshot-cleanup-daily \
  --targets '[{"Id": "1", "Arn": "arn:aws:lambda:us-east-1:111111111111:function:rds-snapshot-lifecycle-cleanup"}]'

# Allow EventBridge to invoke the Lambda
aws lambda add-permission \
  --function-name rds-snapshot-lifecycle-cleanup \
  --statement-id EventBridgeInvoke \
  --action lambda:InvokeFunction \
  --principal events.amazonaws.com \
  --source-arn arn:aws:events:us-east-1:111111111111:rule/rds-snapshot-cleanup-daily
```

## Lambda IAM policy (least privilege)

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "rds:DescribeDBSnapshots",
        "rds:DescribeDBClusterSnapshots",
        "rds:ListTagsForResource"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "rds:DeleteDBSnapshot",
        "rds:DeleteDBClusterSnapshot"
      ],
      "Resource": [
        "arn:aws:rds:*:111111111111:snapshot:*",
        "arn:aws:rds:*:111111111111:cluster-snapshot:*"
      ]
    }
  ]
}
```

## CloudWatch alarm for cleanup failures

```bash
aws cloudwatch put-metric-alarm \
  --alarm-name rds-snapshot-cleanup-failures \
  --metric-name Errors \
  --namespace AWS/Lambda \
  --dimensions Name=FunctionName,Value=rds-snapshot-lifecycle-cleanup \
  --threshold 1 \
  --comparison-operator GreaterThanOrEqualToThreshold \
  --period 300 \
  --evaluation-periods 1 \
  --alarm-actions arn:aws:sns:us-east-1:111111111111:ops-alerts
```

## DR snapshot pipeline with DLM

For automated cross-region snapshot copies without custom Lambda:

```bash
# Create DLM policy for RDS cross-region DR
aws dlm create-lifecycle-policy \
  --description "RDS cross-region DR snapshots" \
  --state ENABLED \
  --execution-role-arn arn:aws:iam::111111111111:role/AWSDataLifecycleManagerDefaultRole \
  --policy-details '{
    "PolicyType": "EBS_SNAPSHOT_MANAGEMENT",
    "ResourceTypes": ["INSTANCE"],
    "TargetTags": [{"Key": "DRPolicy", "Value": "enabled"}],
    "Schedules": [{
      "Name": "DailySnapshots",
      "CreateRule": {"Interval": 24, "IntervalUnit": "HOURS", "Times": ["02:00"]},
      "RetainRule": {"Count": 7},
      "CopyTags": true,
      "CrossRegionCopyRules": [{
        "TargetRegion": "us-west-2",
        "Encrypted": true,
        "CmkArn": "arn:aws:kms:us-west-2:111111111111:key/dr-cmk",
        "RetainRule": {"Interval": 7, "IntervalUnit": "DAYS"}
      }]
    }]
  }'
```

## DR snapshot pipeline with AWS Backup

For centralized backup governance with cross-region copy:

```bash
# Create backup plan with cross-region copy rule
aws backup create-backup-plan \
  --backup-plan '{
    "BackupPlanName": "rds-dr-backup-plan",
    "Rules": [{
      "RuleName": "DailyBackup",
      "TargetBackupVaultName": "Default",
      "ScheduleExpression": "cron(0 2 * * ? *)",
      "StartWindowMinutes": 60,
      "CompletionWindowMinutes": 1440,
      "Lifecycle": {"DeleteAfterDays": 7},
      "CopyActions": [{
        "DestinationBackupVaultArn": "arn:aws:backup:us-west-2:111111111111:backup-vault:DRVault",
        "Lifecycle": {"DeleteAfterDays": 7}
      }]
    }]
  }'
```
