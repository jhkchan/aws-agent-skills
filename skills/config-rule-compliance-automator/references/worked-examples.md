# Worked Examples (load on demand) — Config Rule Compliance Automator

Secondary worked examples and full CLI payloads moved verbatim from SKILL.md. Loaded on demand.

---

## Step 3 — Build a custom Lambda rule (full evaluator + deploy CLI) (moved from SKILL.md)

```python
import json, boto3
config = boto3.client('config')

def lambda_handler(event, context):
    invoking_event = json.loads(event['invokingEvent'])
    item = invoking_event['configurationItem']
    compliance = 'NON_COMPLIANT'
    annotation = ''

    if item['resourceType'] == 'AWS::EC2::SecurityGroup':
        if item.get('configuration', {}).get('groupName') == 'default':
            ingress = item.get('configuration', {}).get('ipPermissions', [])
            if ingress:
                annotation = 'Default security group has ingress rules'
            else:
                compliance = 'COMPLIANT'
        else:
            compliance = 'COMPLIANT'

    config.put_evaluations(Evaluations=[{
        'ComplianceResourceType': item['resourceType'],
        'ComplianceResourceId': item['resourceId'],
        'ComplianceType': compliance,
        'Annotation': annotation,
        'OrderingTimestamp': item['configurationItemCaptureTime']
    }], ResultToken=event.get('resultToken', 'NoTokenFound'))
    return {'compliance': compliance}
```

Deploy:

```bash
aws configservice put-config-rule \
  --config-rule '{
    "ConfigRuleName": "custom-default-sg-no-ingress",
    "Source": {
      "Owner": "CUSTOM_LAMBDA",
      "SourceIdentifier": "arn:aws:lambda:us-east-1:111111111111:function:custom-default-sg-check",
      "SourceDetails": [{"EventSource": "aws.config", "MessageType": "ConfigurationItemChangeNotification"}]
    },
    "Scope": {"ComplianceResourceTypes": ["AWS::EC2::SecurityGroup"]}
  }'
```

---

## Step 4 — Deploy conformance packs via StackSets (CLI) (moved from SKILL.md)

```bash
aws cloudformation create-stack-set \
  --stack-set-name cis-compliance-baseline \
  --template-body file://cis-conformance-pack.yaml \
  --capabilities CAPABILITY_IAM CAPABILITY_NAMED_IAM \
  --permission-model SERVICE_MANAGED \
  --auto-deployment Enabled=true,RetainStacksOnAccountRemoval=false

aws cloudformation create-stack-instances \
  --stack-set-name cis-compliance-baseline \
  --deployment-targets OrganizationalUnitIds=["ou-xxxx-root"] \
  --regions us-east-1,us-west-2,eu-west-1,ap-southeast-2
```

Verify:

```bash
aws configservice describe-conformance-packs --region us-east-1
aws configservice describe-conformance-pack-compliance \
  --conformance-pack-name cis-compliance-baseline
```

---

## Step 6 — CIS conformance pack (sample YAML) (moved from SKILL.md)

**CIS conformance pack (sample):**

```yaml
Resources:
  RootAccessKeyCheck:
    Type: AWS::Config::ConfigRule
    Properties:
      ConfigRuleName: root-access-key-check
      Source: {Owner: AWS, SourceIdentifier: IAM_ROOT_ACCESS_KEY_CHECK}

  S3EncryptionRule:
    Type: AWS::Config::ConfigRule
    Properties:
      ConfigRuleName: s3-bucket-server-side-encryption-enabled
      Source: {Owner: AWS, SourceIdentifier: S3_BUCKET_SERVER_SIDE_ENCRYPTION_ENABLED}
      Scope: {ComplianceResourceTypes: [AWS::S3::Bucket]}

  S3EncryptionRemediation:
    Type: AWS::Config::RemediationConfiguration
    Properties:
      ConfigRuleName: !Ref S3EncryptionRule
      TargetType: SSM_DOCUMENT
      TargetId: AWS-EnableS3BucketEncryption
      Automatic: true
      MaximumAutomaticAttempts: 3
      RetryAttemptSeconds: 600
      Parameters:
        S3BucketName: {ResourceValue: {Value: RESOURCE_ID}}
        AutomationAssumeRole:
          StaticValue:
            Values: [!Sub 'arn:aws:iam::${AWS::AccountId}:role/aws-service-role/AmazonSSMAutomationRole/AWS-SSM-AutomationExecutionRole']

  ComplianceSNSTopic:
    Type: AWS::SNS::Topic
    Properties:
      TopicName: config-compliance-notifications
```

---

## Worked example — REVIEW_REQUIRED, Aggregator missing (moved from SKILL.md)

```text
COMPLIANCE: multi-account-cis-baseline
FRAMEWORK: CIS AWS Foundations Benchmark
RULES:
  - Managed: root-account-mfa-enabled, iam-root-access-key-check, cloudtrail-enabled
  - Custom: custom-default-sg-no-ingress (CIS 2.1 gap — no managed equivalent)
REMEDIATION:
  - Automatic: none
  - Manual: custom-default-sg-no-ingress → Custom-RevokeDefaultSGIngress (requires build + test)
AGGREGATOR:
  - Status: NOT CONFIGURED
  - Scope: N/A
FRAMEWORK_DEPLOYMENT:
  - Method: StackSet (cis-compliance-baseline)
  - Auto-deployment: disabled
  - Regions: us-east-1 only
VERDICT: REVIEW_REQUIRED
GAP: (1) Config Aggregator not configured — deploy org aggregator for cross-account visibility. (2) Auto-deployment disabled — new accounts won't receive rules. (3) Multi-region missing — rules in us-east-1 only.
```
