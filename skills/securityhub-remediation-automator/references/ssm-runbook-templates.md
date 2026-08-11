# SSM Automation Runbook Templates

## Common Remediation Runbooks

### S3 Public Access Block
```yaml
---
schemaVersion: '0.3'
description: Block S3 public access on finding
assumeRole: '{{ AutomationAssumeRole }}'
parameters:
  AutomationAssumeRole:
    type: String
  BucketName:
    type: String
mainSteps:
  - name: BlockPublicAccess
    action: aws:executeAwsApi
    inputs:
      Service: s3control
      Api: PutPublicAccessBlock
      Parameters:
        PublicAccessBlockConfiguration:
          BlockPublicAcls: true
          IgnorePublicAcls: true
          BlockPublicPolicy: true
          RestrictPublicBuckets: true
        AccountId: '{{ global:ACCOUNT_ID }}'
```

### IAM Access Key Revocation
```yaml
---
schemaVersion: '0.3'
description: Deactivate exposed IAM access key
mainSteps:
  - name: DeactivateKey
    action: aws:executeAwsApi
    inputs:
      Service: iam
      Api: UpdateAccessKey
      Parameters:
        AccessKeyId: '{{ AccessKeyId }}'
        Status: Inactive
```

### Security Group Remediation
```yaml
---
schemaVersion: '0.3'
description: Remove overly permissive ingress rule
mainSteps:
  - name: RevokeRule
    action: aws:executeAwsApi
    inputs:
      Service: ec2
      Api: RevokeSecurityGroupIngress
      Parameters:
        GroupId: '{{ GroupId }}'
        IpPermissions: '{{ IpPermissions }}'
```

## EventBridge Rule Pattern for Security Hub
```json
{
  "source": ["aws.securityhub"],
  "detail-type": ["Security Hub Finding"],
  "detail": {
    "findings": {
      "Severity": {"Label": ["CRITICAL", "HIGH"]},
      "Workflow": {"Status": ["NEW"]}
    }
  }
}
```

## Severity-Based SLA
| Severity | Auto-Remediate | Notify Only |
|---|---|---|
| Critical | < 5 min | - |
| High | < 1 hour | - |
| Medium | - | SNS/Slack |
| Low | - | Daily digest |
