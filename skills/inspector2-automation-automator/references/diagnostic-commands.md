# Inspector2 Automation Automator — diagnostic & deployment commands (moved verbatim from SKILL.md)

> Progressive-disclosure split: this content was moved verbatim from SKILL.md; nothing was rewritten.

## Step 2 — Enable Inspector (EC2 / ECR / Lambda)

```bash
aws inspector2 enable \
  --account-ids 111111111111 \
  --client-token $(uuidgen) \
  --ec2 \
  --ecr \
  --lambda
```

Verify coverage:

```bash
aws inspector2 list-coverage \
  --filter-criteria accountId=111111111111
```

For multi-account via delegated admin:

```bash
# In the management account
aws inspector2 enable \
  --account-ids 111111111111 222222222222 333333333333 \
  --ec2 --ecr --lambda

# Designate delegated admin
aws organizations register-delegated-administrator \
  --account-id 111111111111 \
  --service-principal inspector2.amazonaws.com
```

## Step 5 — Wire EventBridge rule for findings

```bash
aws events put-rule \
  --name inspector-critical-auto-patch \
  --event-pattern '{
    "source": ["aws.inspector2"],
    "detail-type": ["Inspector Finding"],
    "detail": {
      "severity": ["CRITICAL"],
      "status": ["OPEN"]
    }
  }'

aws events put-targets \
  --rule inspector-critical-auto-patch \
  --targets '[{"Id":"inspector-patch-ssm","Arn":"arn:aws:ssm:us-east-1:111111111111:automation-definition/AWS-RunPatchBaseline","RoleArn":"arn:aws:iam::111111111111:role/service-role/AmazonInspectorEventBridgeInvokeSSM"}]'
```

Or route to Lambda for triage logic:

```bash
aws events put-targets \
  --rule inspector-critical-auto-patch \
  --targets '[{"Id":"inspector-triage-lambda","Arn":"arn:aws:lambda:us-east-1:111111111111:function:inspector-finding-triage","DeadLetterConfig":{"Arn":"arn:aws:sqs:us-east-1:111111111111:inspector-finding-dlq"}}]'
```

Lambda handler:

```python
import boto3, json
ssm = boto3.client('ssm')
inspector = boto3.client('inspector2')

def lambda_handler(event, context):
    finding = event['detail']
    finding_arn = finding['findingArn']
    severity = finding['severity']
    resource = finding['resources'][0]

    if resource['type'] == 'AWS_EC2_INSTANCE':
        instance_id = resource['details']['awsEc2Instance']['instanceId']

        if severity == 'CRITICAL':
            # Auto-patch
            ssm.start_automation_execution(
                DocumentName='AWS-RunPatchBaseline',
                DocumentVersion='1',
                Parameters={
                    'InstanceId': [instance_id],
                    'Operation': ['Install'],
                    'RebootOption': ['RebootIfNeeded']
                },
                Mode='Auto'
            )
            return {'statusCode': 200, 'body': f'Started patch for {instance_id}'}

    elif resource['type'] == 'AWS_ECR_CONTAINER_IMAGE':
        # Trigger rebuild via CodeBuild
        cb = boto3.client('codebuild')
        cb.start_build(
            projectName='container-rebuild-pipeline',
            environmentVariablesOverride=[{
                'name': 'VULNERABLE_IMAGE',
                'value': resource['details']['awsEcrContainerImage']['imageName']
            }]
        )

    return {'statusCode': 200, 'body': 'No action'}
```

## Step 8 — ECR image scan on push + rebuild trigger

Enable scan-on-push per repository:

```bash
aws ecr put-image-scanning-configuration \
  --repository-name prod-app \
  --image-scanning-configuration scanOnPush=true
```

For scheduled rescan of existing images:

```bash
# EventBridge cron rule: weekly rescan
aws events put-rule \
  --name ecr-weekly-rescan \
  --schedule-expression "cron(0 6 ? * MON *)" \
  --state ENABLED

aws events put-targets \
  --rule ecr-weekly-rescan \
  --targets '[{"Id":"ecr-rescan-lambda","Arn":"arn:aws:lambda:us-east-1:111111111111:function:ecr-batch-rescan"}]'
```

Lambda handler:

```python
import boto3
ecr = boto3.client('ecr')

def lambda_handler(event, context):
    repos = ecr.describe_repositories(maxResults=50)
    for repo in repos['repositories']:
        images = ecr.list_images(repositoryName=repo['repositoryName'], maxResults=100)
        for img in images['imageIds']:
            try:
                ecr.start_image_scan(
                    repositoryName=repo['repositoryName'],
                    imageId={'imageDigest': img['imageDigest']}
                )
            except Exception as e:
                print(f'Skip {img}: {e}')
    return {'statusCode': 200}
```

Container rebuild trigger via CodeBuild:

```bash
aws events put-rule \
  --name inspector-ecr-rebuild-trigger \
  --event-pattern '{
    "source": ["aws.inspector2"],
    "detail-type": ["Inspector Finding"],
    "detail": {
      "severity": ["CRITICAL"],
      "status": ["OPEN"],
      "resources": {
        "type": ["AWS_ECR_CONTAINER_IMAGE"]
      }
    }
  }'

aws events put-targets \
  --rule inspector-ecr-rebuild-trigger \
  --targets '[{"Id":"codebuild-rebuild","Arn":"arn:aws:codebuild:us-east-1:111111111111:project/container-rebuild-pipeline","RoleArn":"arn:aws:iam::111111111111:role/service-role/CodeBuildEventBridgeInvoke"}]'
```

## Step 9 — Lambda code scan finding handler

```python
# Lambda triggered by EventBridge on Lambda code scan finding
import boto3, os
lambda_client = boto3.client('lambda')
sns = boto3.client('sns')

def lambda_handler(event, context):
    finding = event['detail']
    function_arn = finding['resources'][0]['details']['awsLambdaFunction']['functionArn']
    function_name = function_arn.split(':')[-1] if ':' in function_arn else function_arn

    # Notify — Lambda patches require code redeploy
    sns.publish(
        TopicArn=os.environ['NOTIFY_TOPIC'],
        Message=f'Inspector finding on Lambda {function_name}: {finding["title"]}\n\n'
                f'Remediation: {finding.get("remediation", {}).get("recommendation", {}).get("text", "n/a")}\n'
                f'Redeploy required: update dependency in build pipeline.'
    )

    # Optional: create a ticket via Jira/ServiceNow API
    return {'statusCode': 200}
```

## Step 10 — Inspector to Security Hub forwarding CLI

Enable integration:

```bash
aws inspector2 batch-update-configuration \
  --ec2-configuration '[]' \
  --ecr-configuration '[]' \
  --lambda-configuration '[]'

# Security Hub integration is enabled by default when both are active
aws securityhub describe-hub  # verify Security Hub is enabled
```

Verify findings are forwarding:

```bash
aws securityhub get-findings \
  --filters 'GeneratorId=[{"Value":"aws-inspector","Comparison":"PREFIX"}]' \
  --query 'Findings[0].[Id,Severity,GeneratorId]' --output json
```

## Step 11 — Finding suppression CLI

```bash
aws inspector2 update-finding \
  --finding-arn arn:aws:inspector2:us-east-1:111111111111:finding/abc123 \
  --status SUPPRESSED

# Or batch update
aws inspector2 batch-update-findings \
  --finding-arns arn:aws:inspector2:us-east-1:111111111111:finding/abc123 arn:aws:inspector2:us-east-1:111111111111:finding/def456 \
  --suppression-reason "Legacy system decommission scheduled 2027-Q1"
```

## Step 11 — Automated suppression (accepted-risk list)

For automated suppression (accepted-risk list):

```python
import boto3
inspector = boto3.client('inspector2')

ACCEPTED_RISKS = {
    'arn:aws:inspector2:us-east-1:111111111111:finding/abc123': 'Legacy CVE, decommission scheduled',
    # ... loaded from DynamoDB
}

def lambda_handler(event, context):
    for arn, reason in ACCEPTED_RISKS.items():
        inspector.update_finding(
            findingArn=arn,
            status='SUPPRESSED',
            suppressionReason=reason
        )
    return {'statusCode': 200}
```

## Step 12 — Multi-account via delegated admin CLI

```bash
# In the management account — designate delegated admin
aws organizations register-delegated-administrator \
  --account-id 111111111111 \
  --service-principal inspector2.amazonaws.com

# In the delegated admin account — enable for all member accounts
aws inspector2 enable \
  --account-ids $(aws organizations list-accounts --query 'Accounts[].Id' --output text | tr '\t' ' ') \
  --ec2 --ecr --lambda
```

Verify member account coverage:

```bash
aws inspector2 list-coverage \
  --filter-criteria accountId=222222222222
```

## Step 13 — SLA enforcement scheduled Lambda

```python
import boto3, os
from datetime import datetime, timedelta
inspector = boto3.client('inspector2')
sns = boto3.client('sns')

SLA = {
    'CRITICAL': 1,   # days
    'HIGH': 7,
    'MEDIUM': 30,
    'LOW': 90,
}

def lambda_handler(event, context):
    now = datetime.utcnow()
    for severity, sla_days in SLA.items():
        cutoff = (now - timedelta(days=sla_days)).isoformat()
        resp = inspector.list_findings(
            filterCriteria={
                'severity': [{'comparison': 'EQUALS', 'value': severity}],
                'status': [{'comparison': 'EQUALS', 'value': 'OPEN'}],
                'updatedAt': [{'comparison': 'LESS_THAN', 'value': cutoff}]
            }
        )
        for finding in resp['findings']:
            sns.publish(
                TopicArn=os.environ['SLA_TOPIC'],
                Message=f'SLA breached: {severity} finding {finding["findingArn"]} open for > {sla_days} days'
            )
    return {'statusCode': 200}
```

## Pre-flight safety checks (run before applying any Inspector CLI)

- **MANDATORY CONFIRMATION GATE.** Before any state-changing
  operation (`inspector2 enable`, `disable`, `update-finding`,
  custom SSM `start-automation-execution`, suppressing findings),
  emit:
  `CONFIRM: About to <action> for finding/coverage <id> in account
  <account>. This affects <consequence>. Proceed? (yes/no)`

- **Snapshot the target EC2 instances** before any patching:
  `aws ec2 create-image --instance-id i-0abc123 --name "pre-inspector-patch-$(date +%s)" --no-reboot`

- **Before auto-patching Critical findings in production**, run
  the patch baseline in `Operation: Scan` mode for 1 week in
  pre-prod to validate the baseline contents. Then promote to
  `Install` mode.

- **Before deploying Inspector multi-account**, verify the
  delegated admin account is correctly designated via
  `aws inspector2 list-delegated-admin-accounts`.

- **For container rebuild automation**, dry-run the CodeBuild
  project manually with a test finding payload to verify the
  build pipeline produces a patched image without exhausting
  concurrent build limits.
