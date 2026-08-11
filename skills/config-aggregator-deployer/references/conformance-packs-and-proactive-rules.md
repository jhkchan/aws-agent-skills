# Conformance Packs, Proactive Rules, and Lambda Processors — Config Aggregator Deployer

Deep reference on conformance pack templates, proactive rule
evaluation lifecycle, Lambda processor rule patterns, and
multi-account compliance query patterns via aggregator APIs.

## Conformance packs

### What they are

A conformance pack is a collection of AWS Config rules and
remediation actions that are deployed as a single entity. They are
defined in YAML templates and can be deployed at two scopes:

| Scope | Deploy API | Applies to | Override behavior |
|---|---|---|---|
| **Organization** | `PutOrganizationConformancePack` | All accounts in the Organization (current + future) | Individual account packs of the same name override org-level |
| **Account** | `PutConformancePack` | Single account only | Does NOT affect other accounts |

**Rule:** use organization conformance packs for enterprise-wide
compliance. Reserve individual account packs for exceptions.

### AWS sample conformance pack templates

AWS provides pre-built templates aligned to common compliance
frameworks:

| Template | Framework | Coverage |
|---|---|---|
| `OperationalBestPractices-for-Security` | AWS security best practices | IAM, S3, EC2, CloudTrail, Config |
| `OperationalBestPractices-for-CloudWatch` | CloudWatch monitoring | Alarms, logs, dashboards |
| `OperationalBestPractices-for-EC2` | EC2 best practices | Instance type, EBS encryption, security groups |
| `OperationalBestPractices-for-S3` | S3 best practices | Versioning, encryption, public access |
| `OperationalBestPractices-for-IAM` | IAM best practices | Password policy, MFA, key rotation |
| `FedRAMP-moderate` | FedRAMP Moderate | NIST 800-53 controls |
| `HIPAA-Security` | HIPAA Security Rule | PHI protection controls |
| `PCI-DSS` | PCI DSS 3.2.1 | Cardholder data environment controls |
| `CIS-AWS` | CIS AWS Foundations Benchmark | Level 1 + Level 2 controls |

### Template structure

```yaml
Resources:
  S3BucketVersioningCheck:
    Type: AWS::Config::ConfigRule
    Properties:
      ConfigRuleName: s3-bucket-versioning-check
      Source:
        Owner: AWS
        SourceIdentifier: S3_BUCKET_VERSIONING_ENABLED
      Scope:
        ComplianceResourceTypes:
          - AWS::S3::Bucket

  S3PublicReadProhibited:
    Type: AWS::Config::ConfigRule
    Properties:
      ConfigRuleName: s3-bucket-public-read-prohibited
      Source:
        Owner: AWS
        SourceIdentifier: S3_BUCKET_PUBLIC_READ_PROHIBITED
      Scope:
        ComplianceResourceTypes:
          - AWS::S3::Bucket

  # Remediation action — auto-remediate non-compliant resources
  S3BucketVersioningRemediation:
    Type: AWS::Config::RemediationConfiguration
    Properties:
      ConfigRuleName: s3-bucket-versioning-check
      TargetType: SSM_DOCUMENT
      TargetId: AWS-EnableS3BucketVersioning
      Automatic: true
      MaximumAutomaticAttempts: 3
      RetryAttemptSeconds: 60
      Parameters:
        BucketName:
          ResourceValue:
            Value: RESOURCE_ID
```

### Org-level deployment with parameters

```bash
aws configservice put-organization-conformance-pack \
  --organization-conformance-pack-name OperationalBestPractices-for-EC2 \
  --template-s3-uri s3://config-templates-123456789012/ec2-best-practices.yaml \
  --conformance-pack-input-parameters \
    ParameterName=DesiredInstanceType,ParameterValue=t3.medium \
    ParameterName=AllowedRegions,ParameterValue=us-east-1 \
  --region us-east-1
```

### Per-account status verification

```bash
aws configservice get-organization-conformance-pack-detailed-status \
  --organization-conformance-pack-name OperationalBestPractices-for-Security \
  --region us-east-1
```

This shows the deployment status for each account — useful for
identifying accounts where the pack failed to deploy.

## Proactive rules

### How proactive evaluation works

Proactive Config rules evaluate resources BEFORE they are created.
Instead of checking resources after a configuration change (reactive),
proactive rules evaluate a hypothetical resource configuration against
compliance rules at deployment time.

**Lifecycle:**
1. Create/update a Config rule with `Proactive: true`.
2. Call `StartResourceEvaluation` with the resource type, ID, and
   hypothetical configuration JSON.
3. Receive an `EvaluationToken`.
4. Poll `GetResourceEvaluationStatus` with the token until status is
   `SUCCEEDED` or `FAILED`.
5. The response includes `ComplianceType` (COMPLIANT / NON_COMPLIANT /
   NOT_APPLICABLE) and evaluation result details.

### Enabling proactive mode

```bash
aws configservice put-config-rule \
  --config-rule '{
    "ConfigRuleName": "s3-bucket-versioning-proactive",
    "Source": {
      "Owner": "AWS",
      "SourceIdentifier": "S3_BUCKET_VERSIONING_ENABLED"
    },
    "Proactive": true
  }' \
  --region us-east-1
```

Not all managed rules support proactive mode. Verify support by
checking the rule's `Proactive` flag in the managed rule description.

### Pre-deployment evaluation

```bash
# Check if a new S3 bucket would be compliant
EVAL_TOKEN=$(aws configservice start-resource-evaluation \
  --resource-type "AWS::S3::Bucket" \
  --resource-id "my-new-bucket" \
  --evaluation-mode PROACTIVE \
  --configuration '{
    "BucketName": "my-new-bucket",
    "VersioningConfiguration": {"Status": "Suspended"},
    "BucketEncryption": {"ServerSideEncryptionConfiguration": []}
  }' \
  --query 'EvaluationToken' --output text \
  --region us-east-1)

# Retrieve result
aws configservice get-resource-evaluation-status \
  --evaluation-token ${EVAL_TOKEN} \
  --region us-east-1
```

### CI/CD integration

Proactive evaluation integrates with CloudFormation hooks, CDK
aspects, and Terraform pre-apply checks. The IaC tool calls
`StartResourceEvaluation` before deploying and blocks if the result
is NON_COMPLIANT.

## Lambda processor rules

### Event schema

When Config invokes a Lambda-backed rule, it sends an event with:

```json
{
  "configRuleName": "custom-encryption-check",
  "configRuleArn": "arn:aws:config:us-east-1:123456789012:config-rule/custom-encryption-check",
  "configRuleId": "config-rule-abc123",
  "configurationItem": {
    "resourceType": "AWS::S3::Bucket",
    "resourceId": "my-bucket",
    "configurationItemStatus": "OK",
    "configuration": { "...": "resource configuration" },
    "awsRegion": "us-east-1",
    "awsAccountId": "111111111111"
  },
  "invokingEvent": "{ \"configurationItemDiff\": \"...\", \"messageType\": \"ConfigurationItemChangeNotification\" }",
  "resultToken": "token-string"
}
```

### Lambda handler pattern

```python
import json
import boto3

config = boto3.client('config')

def handler(event, context):
    config_item = json.loads(event['invokingEvent'])['configurationItem']
    resource_type = config_item['resourceType']
    resource_id = config_item['resourceId']
    configuration = config_item.get('configuration', {})

    # Custom compliance logic
    is_compliant = check_compliance(resource_type, configuration)

    evaluations = [{
        'ComplianceResourceType': resource_type,
        'ComplianceResourceId': resource_id,
        'ComplianceType': 'COMPLIANT' if is_compliant else 'NON_COMPLIANT',
        'Annotation': 'Encryption enabled' if is_compliant else 'Encryption not enabled',
        'OrderingTimestamp': config_item['configurationItemCaptureTime']
    }]

    config.put_evaluations(
        Evaluations=evaluations,
        ResultToken=event['resultToken']
    )

    return {'statusCode': 200}

def check_compliance(resource_type, configuration):
    if resource_type == 'AWS::S3::Bucket':
        enc = configuration.get('serverSideEncryptionConfiguration')
        return enc is not None
    return True
```

### Lambda resource policy

Config needs permission to invoke the Lambda:

```bash
aws lambda add-permission \
  --function-name config-encryption-evaluator \
  --statement-id ConfigInvokePermission \
  --action lambda:InvokeFunction \
  --principal config.amazonaws.com \
  --region us-east-1
```

### Organization custom rule

Deploy the Lambda-backed rule across all accounts:

```bash
aws configservice put-organization-config-rule \
  --organization-config-rule-name custom-encryption-check \
  --organization-custom-rule \
    LambdaFunctionArn=arn:aws:lambda:us-east-1:123456789012:function:config-encryption-evaluator,\
    OrganizationRuleStatus=ENABLED,\
    MaximumExecutionFrequency=One_Hour \
  --region us-east-1
```

The Lambda runs in the delegated admin account but evaluates
resources across all member accounts via Config's cross-account
invocation.

## Multi-account compliance query patterns

### Aggregate compliance summary

```bash
# Overall compliance across all accounts/regions for a specific rule
aws configservice get-aggregate-config-rule-compliance-summary \
  --configuration-aggregator-name org-compliance-aggregator \
  --config-rule-name s3-bucket-versioning-enabled \
  --region us-east-1

# Compliance by account
aws configservice get-aggregate-config-rule-compliance-summary \
  --configuration-aggregator-name org-compliance-aggregator \
  --filters AccountId=111111111111,AwsRegion=us-east-1 \
  --region us-east-1
```

### Non-compliant resources

```bash
# List all non-compliant resources for a rule across accounts
aws configservice get-aggregate-compliance-details-by-config-rule \
  --configuration-aggregator-name org-compliance-aggregator \
  --config-rule-name s3-bucket-versioning-enabled \
  --compliance-type NON_COMPLIANT \
  --region us-east-1
```

### Aggregated discovered resources

```bash
# List all resources of a type across accounts
aws configservice list-aggregate-discovered-resources \
  --configuration-aggregator-name org-compliance-aggregator \
  --resource-type AWS::S3::Bucket \
  --region us-east-1
```
