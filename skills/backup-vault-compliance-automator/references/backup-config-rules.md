# Backup Config Rules Reference

Supplementary reference for the Backup Vault Compliance Automator
skill. Use when deploying AWS Config rules for backup compliance
monitoring, including managed rules, custom Lambda rules, and
aggregation across an Organizations fleet.

## AWS-managed Config rules for backup

| Rule identifier | What it evaluates | Scope | Compliance check |
|---|---|---|---|
| `backup-plan-frequency` | Backup plans meet min frequency | `AWS::Backup::BackupPlan` | Checks the `ScheduleExpression` matches the required frequency |
| `backup-recovery-point-encrypted` | Recovery points use KMS encryption | `AWS::Backup::RecoveryPoint` | Checks `EncryptionKeyArn` is non-null |
| `backup-recovery-point-manual-deletion-disabled` | Vault Lock prevents manual deletion | `AWS::Backup::BackupVault` | Checks `LockState` is `LOCKED` |
| `backup-vaults-are-encrypted` | Backup vaults use KMS encryption | `AWS::Backup::BackupVault` | Checks vault `EncryptionKeyArn` is set |

### Deploy managed rules

```bash
# Recovery point encryption
aws configservice put-config-rule \
  --config-rule '{
    "ConfigRuleName": "backup-recovery-point-encrypted",
    "Source": {
      "Owner": "AWS",
      "SourceIdentifier": "backup-recovery-point-encrypted"
    }
  }' \
  --region us-east-1

# Vault lock enforcement
aws configservice put-config-rule \
  --config-rule '{
    "ConfigRuleName": "backup-vault-lock-enabled",
    "Source": {
      "Owner": "AWS",
      "SourceIdentifier": "backup-recovery-point-manual-deletion-disabled"
    }
  }' \
  --region us-east-1

# Backup plan frequency
aws configservice put-config-rule \
  --config-rule '{
    "ConfigRuleName": "backup-plan-frequency-daily",
    "Source": {
      "Owner": "AWS",
      "SourceIdentifier": "backup-plan-frequency"
    },
    "InputParameters": "{\"requiredFrequency\": \"1d\"}"
  }' \
  --region us-east-1
```

## Custom Config rules for backup coverage

Managed rules do not check whether individual resources (EC2, RDS,
DynamoDB) are covered by backup plans. A custom Lambda rule is needed.

### Lambda function: check-ec2-backup-coverage

```python
import boto3, json

backup = boto3.client('backup')
config = boto3.client('config')

def lambda_handler(event, context):
    # Parse the Config event
    invoking_event = json.loads(event['invokingEvent'])
    config_item = invoking_event.get('configurationItem', {})
    resource_id = config_item.get('resourceId')
    resource_type = config_item.get('resourceType')
    tags = config_item.get('tags', {})

    # Check if the resource has a backup-related tag
    backup_tag = tags.get('BackupPlan')
    compliance_type = 'COMPLIANT' if backup_tag else 'NON_COMPLIANT'
    annotation = f'Resource {resource_id} has BackupPlan={backup_tag}' if backup_tag else f'Resource {resource_id} lacks BackupPlan tag'

    # If tagged, verify the backup plan exists
    if backup_tag:
        try:
            plans = backup.list_backup_plans()
            plan_exists = any(
                p['BackupPlanName'] == backup_tag
                for p in plans.get('BackupPlansList', [])
            )
            if not plan_exists:
                compliance_type = 'NON_COMPLIANT'
                annotation = f'Resource {resource_id} references BackupPlan={backup_tag} but no such plan exists'
        except Exception as e:
            compliance_type = 'NON_COMPLIANT'
            annotation = f'Error checking backup plan: {str(e)}'

    # Evaluate compliance
    config.put_evaluations(
        Evaluations=[{
            'ComplianceResourceType': resource_type,
            'ComplianceResourceId': resource_id,
            'ComplianceType': compliance_type,
            'Annotation': annotation,
            'OrderingTimestamp': invoking_event.get('notificationCreationTime')
        }],
        ResultToken=event.get('resultToken', '')
    )

    return {'statusCode': 200, 'compliance': compliance_type}
```

### Deploy the custom rule

```bash
# Create the Lambda function first
aws lambda create-function \
  --function-name check-ec2-backup-coverage \
  --runtime python3.12 \
  --role arn:aws:iam::111111111111:role/ConfigLambdaRole \
  --handler index.lambda_handler \
  --zip-file fileb://function.zip \
  --timeout 60 \
  --region us-east-1

# Add permission for Config to invoke the Lambda
aws lambda add-permission \
  --function-name check-ec2-backup-coverage \
  --statement-id ConfigInvokePermission \
  --action lambda:InvokeFunction \
  --principal config.amazonaws.com \
  --region us-east-1

# Deploy the Config rule
aws configservice put-config-rule \
  --config-rule '{
    "ConfigRuleName": "ec2-must-have-backup-plan",
    "Description": "EC2 instances must have a BackupPlan tag referencing an active backup plan",
    "Source": {
      "Owner": "CUSTOM_LAMBDA",
      "SourceIdentifier": "arn:aws:lambda:us-east-1:111111111111:function:check-ec2-backup-coverage",
      "SourceDetails": [
        {
          "EventSource": "aws.config",
          "MessageType": "ConfigurationItemChangeNotification"
        },
        {
          "EventSource": "aws.config",
          "MessageType": "ScheduledNotification",
          "MaximumExecutionFrequency": "TwentyFour_Hours"
        }
      ]
    },
    "Scope": {
      "ComplianceResourceTypes": ["AWS::EC2::Instance"]
    }
  }' \
  --region us-east-1
```

### Custom rule: backup frequency compliance

```python
import boto3, json
from datetime import datetime, timedelta

backup = boto3.client('backup')

def lambda_handler(event, context):
    invoking_event = json.loads(event['invokingEvent'])
    config_item = invoking_event.get('configurationItem', {})
    resource_arn = config_item.get('ARN')
    resource_id = config_item.get('resourceId')

    # Check for completed backup jobs in the last 24 hours
    cutoff = datetime.now() - timedelta(hours=24)
    jobs = backup.list_backup_jobs(
        ByResourceArn=resource_arn,
        ByCreatedAfter=cutoff,
        ByState='COMPLETED'
    )

    if jobs['BackupJobs']:
        compliance_type = 'COMPLIANT'
        annotation = f'{len(jobs["BackupJobs"])} backup(s) in last 24h'
    else:
        compliance_type = 'NON_COMPLIANT'
        annotation = 'No completed backup in last 24 hours'

    return {
        'compliance_type': compliance_type,
        'resource_id': resource_id,
        'annotation': annotation
    }
```

## Organizations-wide Config aggregation

### Set up the aggregator in the management account

```bash
aws configservice put-configuration-aggregator \
  --configuration-aggregator-name org-backup-compliance \
  --organization-aggregator-source '{
    "RoleArn": "arn:aws:iam::111111111111:role/ConfigAggregatorRole",
    "AllAwsRegions": true
  }' \
  --region us-east-1
```

### ConfigAggregatorRole trust policy

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {"Service": "config.amazonaws.com"},
    "Action": "sts:AssumeRole"
  }]
}
```

### ConfigAggregatorRole permissions

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["organizations:ListAccounts", "organizations:DescribeOrganization"],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": ["config:PutAggregationAuthorization", "config:DescribeConfigurationAggregators"],
      "Resource": "*"
    }
  ]
}
```

### Enable AWS Config in member accounts via StackSet

```bash
aws cloudformation create-stack-set \
  --stack-set-name config-enable-backup-rules \
  --template-body file://config-backup-rules.yaml \
  --permission-model SERVICE_MANAGED \
  --auto-deployment 'Enabled=true,RetainStacksOnAccountRemoval=false' \
  --capabilities CAPABILITY_IAM \
  --region us-east-1

aws cloudformation create-stack-instances \
  --stack-set-name config-enable-backup-rules \
  --deployment-targets OrganizationalUnitIds='["r-xxxx"]' \
  --regions '["us-east-1","us-west-2"]' \
  --region us-east-1
```

## Config rule CloudFormation template (config-backup-rules.yaml)

```yaml
Resources:
  BackupRecoveryPointEncrypted:
    Type: AWS::Config::ConfigRule
    Properties:
      ConfigRuleName: backup-recovery-point-encrypted
      Source:
        Owner: AWS
        SourceIdentifier: backup-recovery-point-encrypted

  BackupVaultLockEnabled:
    Type: AWS::Config::ConfigRule
    Properties:
      ConfigRuleName: backup-vault-lock-enabled
      Source:
        Owner: AWS
        SourceIdentifier: backup-recovery-point-manual-deletion-disabled

  ConfigRuleLambdaRole:
    Type: AWS::IAM::Role
    Properties:
      AssumeRolePolicyDocument:
        Version: "2012-10-17"
        Statement:
          - Effect: Allow
            Principal:
              Service: lambda.amazonaws.com
            Action: sts:AssumeRole
      ManagedPolicyArns:
        - arn:aws:iam::aws:policy/service-role/AWSConfigRulesExecutionRole
        - arn:aws:iam::aws:policy/AWSBackupReadOnlyAccess
      Policies:
        - PolicyName: ConfigPutEvaluations
          PolicyDocument:
            Version: "2012-10-17"
            Statement:
              - Effect: Allow
                Action: config:PutEvaluations
                Resource: "*"

  BackupCoverageFunction:
    Type: AWS::Lambda::Function
    Properties:
      FunctionName: check-ec2-backup-coverage
      Runtime: python3.12
      Handler: index.lambda_handler
      Role: !GetAtt ConfigRuleLambdaRole.Arn
      Timeout: 60
      Code:
        ZipFile: |
          import boto3, json
          backup = boto3.client('backup')
          config = boto3.client('config')
          def lambda_handler(event, context):
              invoking_event = json.loads(event['invokingEvent'])
              config_item = invoking_event.get('configurationItem', {})
              resource_id = config_item.get('resourceId', 'unknown')
              tags = config_item.get('tags', {})
              backup_tag = tags.get('BackupPlan')
              if backup_tag:
                  compliance_type = 'COMPLIANT'
                  annotation = f'BackupPlan={backup_tag}'
              else:
                  compliance_type = 'NON_COMPLIANT'
                  annotation = 'Missing BackupPlan tag'
              config.put_evaluations(
                  Evaluations=[{
                      'ComplianceResourceType': 'AWS::EC2::Instance',
                      'ComplianceResourceId': resource_id,
                      'ComplianceType': compliance_type,
                      'Annotation': annotation,
                      'OrderingTimestamp': invoking_event.get('notificationCreationTime')
                  }],
                  ResultToken=event.get('resultToken', '')
              )
              return {'statusCode': 200}

  BackupCoverageConfigPermission:
    Type: AWS::Lambda::Permission
    Properties:
      FunctionName: !Ref BackupCoverageFunction
      Action: lambda:InvokeFunction
      Principal: config.amazonaws.com
      StatementId: ConfigInvokePermission

  EC2BackupCoverageRule:
    Type: AWS::Config::ConfigRule
    Properties:
      ConfigRuleName: ec2-must-have-backup-plan
      Source:
        Owner: CUSTOM_LAMBDA
        SourceIdentifier: !GetAtt BackupCoverageFunction.Arn
        SourceDetails:
          - EventSource: aws.config
            MessageType: ConfigurationItemChangeNotification
          - EventSource: aws.config
            MessageType: ScheduledNotification
            MaximumExecutionFrequency: TwentyFour_Hours
      Scope:
        ComplianceResourceTypes:
          - AWS::EC2::Instance
```

## Querying aggregated compliance

```bash
# Check compliance across all accounts in the aggregator
aws configservice get-aggregate-compliance-details-by-config-rule \
  --configuration-aggregator-name org-backup-compliance \
  --config-rule-name backup-recovery-point-encrypted \
  --account-id 222222222222 \
  --aws-region us-east-1 \
  --region us-east-1

# Get summary of non-compliant resources across all accounts
aws configservice get-aggregate-discovered-resource-counts \
  --configuration-aggregator-name org-backup-compliance \
  --filters '{"ComplianceType": "NON_COMPLIANT"}' \
  --region us-east-1
```

## Remediation configuration for coverage gap

```bash
# Auto-remediate: tag EC2 instances that lack BackupPlan
aws configservice put-remediation-configurations \
  --remediation-configurations '[
    {
      "ConfigRuleName": "ec2-must-have-backup-plan",
      "TargetType": "SSM_DOCUMENT",
      "TargetId": "AWS-TagResource",
      "Automatic": false,
      "Parameters": {
        "ResourceARN": {"ResourceValue": {"Value": "RESOURCE_ID"}},
        "Tags": {"StaticValue": {"Values": ["BackupPlan=prod"]}}
      }
    }
  ]'
```
