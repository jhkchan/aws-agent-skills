# Worked Examples — Tag Governance Automator

> Moved verbatim from SKILL.md for progressive disclosure (agentskills.io). Load on demand.

## Step 7: Automated remediation (Config → SSM → Config re-evaluate)

When Config detects a missing required tag, wire a remediation that
adds a default or derived tag value, then Config re-evaluates and the
resource flips to COMPLIANT.

**Pattern A — SSM Automation document (custom, per resource type):**

```yaml
---
schemaVersion: '0.3'
assumeRole: '{{ AutomationAssumeRole }}'
description: 'Add missing required tags to an EC2 instance'
parameters:
  InstanceId:
    type: String
    description: 'Injected by Config via RESOURCE_ID'
  AutomationAssumeRole:
    type: String
mainSteps:
  - name: CheckCurrentTags
    action: aws:executeAwsApi
    inputs:
      Service: ec2
      Api: DescribeTags
      Filters:
        - Name: resource-id
          Values: ['{{ InstanceId }}']
    outputs:
      - Name: ExistingKeys
        Selector: '$.Tags[].Key'
        Type: StringList
  - name: ApplyDefaultTags
    action: aws:executeAwsApi
    inputs:
      Service: ec2
      Api: CreateTags
      Resources: ['{{ InstanceId }}']
      Tags:
        - {Key: Environment, Value: unknown}
        - {Key: Owner, Value: platform-team}
        - {Key: Project, Value: unassigned}
        - {Key: CostCenter, Value: cc-9999}
    isCritical: true
    onFailure: abort
```

Wire remediation (default tags are placeholders — human review required
to set correct values):

```bash
aws configservice put-remediation-configurations \
  --remediation-configurations '[{
    "ConfigRuleName": "required-tags-core",
    "TargetType": "SSM_DOCUMENT",
    "TargetId": "Custom-AddRequiredTagsEC2",
    "Automatic": false,
    "MaximumAutomaticAttempts": 3,
    "RetryAttemptSeconds": 600,
    "Parameters": {
      "InstanceId": {"ResourceValue": {"Value": "RESOURCE_ID"}},
      "AutomationAssumeRole": {"StaticValue": {"Values": ["arn:aws:iam::111111111111:role/aws-service-role/AmazonSSMAutomationRole/AWS-SSM-AutomationExecutionRole"]}}
    }
  }]'
```

**Pattern B — EventBridge → Lambda (more flexible, branch by type):**

```bash
aws events put-rule \
  --name config-required-tags-noncompliant \
  --event-pattern '{
    "source": ["aws.config"],
    "detail-type": ["Config Rules Compliance Changed"],
    "detail": {
      "newEvaluationResult": {"complianceType": ["NON_COMPLIANT"]},
      "configRuleName": ["required-tags-core"]
    }
  }'
```

Lambda reads the resource, derives a best-guess tag (account → Environment,
creator from CloudTrail), and tags the resource. Idempotency is
critical — the same resource may emit NON_COMPLIANT multiple times.

**Critical:** remediation that stamps `Environment: unknown` is a
placeholder, not a fix. The verdict is AUTOMATED for the workflow
pipeline but flag a secondary manual step to correct the placeholder
values. Do NOT set `Automatic: true` on placeholder remediations
without a downstream human-correction queue.

## ABAC policy pattern — team-scoped S3 access (moved from SKILL.md)

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["s3:GetObject", "s3:PutObject", "s3:DeleteObject"],
      "Resource": "arn:aws:s3:::team-data-*/*",
      "Condition": {
        "StringEquals": {
          "aws:ResourceTag/Team": "${aws:PrincipalTag/Team}"
        }
      }
    },
    {
      "Effect": "Allow",
      "Action": "s3:CreateBucket",
      "Resource": "arn:aws:s3:::*",
      "Condition": {
        "StringEquals": {
          "aws:RequestTag/Team": "${aws:PrincipalTag/Team}"
        },
        "ForAllValues:StringEquals": {
          "aws:TagKeys": ["Team", "Environment", "Owner"]
        }
      }
    }
  ]
}
```

## Worked example — MANUAL_STEP_REQUIRED, cost allocation activation on legacy account

```text
GOVERNANCE: legacy-account-cost-tags
SCOPE: account 222222222222 (legacy, pre-2020)
STRATEGY:
  - Required tags: Environment, Owner, CostCenter
  - Optional tags: none
  - Enforcement layer: Config required-tags (already deployed)
POLICY:
  - Type: Cost allocation tag activation
  - Attached to: payer account 222222222222
  - Template: N/A — manual console step required
AUTOMATION:
  - Auto-tagging: N/A (already deployed via EventBridge)
  - Remediation: N/A
  - Trigger: N/A
COMPLIANCE:
  - Detection: required-tags-core (already firing)
  - Reporting: Config dashboard only (no Cost Explorer dimension — tags inactive)
  - Cost allocation: INACTIVE — cannot activate via API on this account
VERDICT: MANUAL_STEP_REQUIRED
GAP: Account 222222222222 does not support ce update-cost-allocation-tags-status (IAM policy restriction on payer). Manual step required: Billing console -> Cost Allocation Tags -> activate Environment, Owner, CostCenter. Propagation takes up to 24 hours.
TEMPLATE: (manual console step — no API path available for this account)
```
