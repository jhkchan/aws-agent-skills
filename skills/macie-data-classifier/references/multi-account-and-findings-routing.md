# Multi-Account Topology and Findings Routing — Macie Data Classifier

Deep reference on Macie administrator/member delegation via AWS
Organizations, member association and status lifecycle, Security Hub
integration mechanics (per-Region export), CloudWatch Events /
EventBridge rule configuration for automated response, and the ASDD
auto-enable flow. Loaded on demand by the skill.

## Macie multi-account architecture

### Administrator/member model

Macie uses a delegated administrator model within AWS Organizations.
The administrator account manages Macie for all member accounts.

```text
AWS Organization
  └── Macie Administrator Account (delegated admin)
        ├── Member Account A (ENABLED — Macie active)
        ├── Member Account B (ENABLED — Macie active)
        ├── Member Account C (PAUSED — Macie paused)
        ├── Member Account D (INVITED — not yet accepted)
        └── Account E (NOT_ENROLLED — not invited)
```

### Delegated administrator setup

```bash
# Designate the Macie administrator account (run in org management account)
aws organizations register-delegated-administrator \
  --account-id 123456789012 \
  --service-principal macie.amazonaws.com

# Verify delegation
aws organizations list-delegated-administrators \
  --service-principal macie.amazonaws.com
```

### Enable Macie in the administrator account

```bash
aws macie2 enable-macie-session \
  --finding-publishing-frequency FIFTEEN_MINUTES \
  --region us-east-1

# Enable ASDD with org-wide auto-enable
aws macie2 update-automated-discovery-configuration \
  --status ENABLED \
  --auto-enable-organization-members \
  --region us-east-1
```

### Member account lifecycle

| Status | Meaning | Coverage |
|---|---|---|
| `ENABLED` | Macie is active in the member account | Full coverage |
| `PAUSED` | Macie is temporarily paused | No scanning — gap |
| `INVITED` | Invitation sent but not accepted | No scanning — gap |
| `DISASSOCIATED` | Member was removed | No scanning — gap |
| `NOT_ENROLLED` | Account not in Macie member list | No scanning — gap |

### Invite member accounts

```bash
# Create member invitations
aws macie2 create-members \
  --accounts '[{"accountId":"111111111111"},{"accountId":"222222222222"}]' \
  --region us-east-1

# Or auto-associate all org accounts (with ASDD auto-enable)
aws macie2 update-organization-configuration \
  --auto-enable true \
  --region us-east-1
```

### Effective coverage calculation

```text
Organization accounts:       150
Macie member accounts:       142  (8 not enrolled)
  ENABLED:                   135
  PAUSED:                      5  (coverage gap)
  INVITED (not accepted):      2  (coverage gap)

Effective coverage: 135 / 150 = 90.0%
Gap: 15 accounts (10%) with no Macie scanning
```

## Security Hub integration

### How Macie publishes to Security Hub

Macie publishes findings to AWS Security Hub when:
1. Security Hub is enabled in the same account and Region
2. Macie's Security Hub integration is enabled
3. The finding is not suppressed by a findings filter

**Enable Security Hub integration:**

```bash
# Ensure Security Hub is enabled
aws securityhub enable-security-hub --region us-east-1

# Macie auto-publishes to Security Hub when both are enabled
# Verify Macie findings in Security Hub
aws securityhub get-findings \
  --filters '{"ProductName":[{"Value":"Macie","Comparison":"EQUALS"}]}' \
  --region us-east-1 \
  --query 'Findings[*].{Id:Id,Severity:Severity.Severity,Type:Type,Time:UpdatedAt}' \
  --output table
```

### Per-Region export

Macie findings are regional. Security Hub integration is per-Region.
An organization operating in us-east-1 and eu-west-1 must:

1. Enable Macie in both Regions
2. Enable Security Hub in both Regions
3. (Optional) Configure Security Hub aggregation to collect all
   findings in one Region

```bash
# Configure Security Hub aggregation (us-east-1 as aggregator)
aws securityhub create-finding-aggregator \
  --region us-east-1 \
  --region-linking-mode ALL_REGIONS
```

## CloudWatch Events / EventBridge integration

### Event pattern for Macie findings

```json
{
  "source": ["aws.macie"],
  "detail-type": ["Macie Finding"],
  "detail": {
    "severity": ["High"]
  }
}
```

### Create EventBridge rule for Macie findings

```bash
# Create the rule
aws events put-rule \
  --name "macie-high-severity-finding" \
  --event-pattern '{
    "source": ["aws.macie"],
    "detail-type": ["Macie Finding"],
    "detail": { "severity": ["High"] }
  }' \
  --region us-east-1

# Add Lambda target for auto-remediation
aws events put-targets \
  --rule "macie-high-severity-finding" \
  --targets '[{"Id":"macie-remediation-lambda","Arn":"arn:aws:lambda:us-east-1:123456789012:function:macie-auto-remediation"}]' \
  --region us-east-1

# Add Lambda permission for EventBridge
aws lambda add-permission \
  --function-name macie-auto-remediation \
  --statement-id macie-eventbridge \
  --action lambda:InvokeFunction \
  --principal events.amazonaws.com \
  --source-arn arn:aws:events:us-east-1:123456789012:rule/macie-high-severity-finding \
  --region us-east-1
```

### Automated remediation Lambda pattern

```python
import json
import boto3

s3 = boto3.client('s3')

def lambda_handler(event, context):
    finding = event['detail']
    severity = finding.get('severity', 'Unknown')
    finding_type = finding.get('type', 'Unknown')

    if severity == 'High':
        # Example: block public access on a bucket with credentials
        bucket_name = finding.get('resources', [{}])[0].get('bucketName')
        if bucket_name:
            s3.put_public_access_block(
                Bucket=bucket_name,
                PublicAccessBlockConfiguration={
                    'BlockPublicAcls': True,
                    'IgnorePublicAcls': True,
                    'BlockPublicPolicy': True,
                    'RestrictPublicBuckets': True
                }
            )
            print(f"Blocked public access on {bucket_name}")

    return {'statusCode': 200, 'body': json.dumps('Remediation complete')}
```

## Suppression rules (findings filters) deep reference

### SUPPRESS vs ARCHIVE

| Action | Effect on Macie console | Security Hub | CloudWatch Events |
|---|---|---|---|
| `SUPPRESS` | Finding hidden | Not published | Not published |
| `ARCHIVE` | Finding archived (filterable) | Not published | Published (then archived) |
| `NO_PURPOSE` | Finding visible | Published | Published |

**Audit recommendation:** use `ARCHIVE` for noise reduction (findings
remain discoverable). Use `SUPPRESS` only for known false positives with
documented justification. NEVER use `SUPPRESS` on High severity findings.

### Findings filter structure

```bash
aws macie2 create-findings-filter \
  --name "archive-known-public-buckets" \
  --action ARCHIVE \
  --finding-criteria '{
    "criterion": {
      "type": { "eq": ["Policy:IAMUser/S3/BucketPublic"] },
      "resourcesS3BucketArn": { "contains": ["public-assets"] }
    }
  }' \
  --region us-east-1
```

### Dangerous filter detection patterns

```text
RED FLAGS to flag in audit:

1. action: SUPPRESS + severity includes "High"
   → Suppressed High severity findings are hidden from SOC

2. action: SUPPRESS + no narrow criteria
   → Broad suppression masks unknown findings

3. action: SUPPRESS + type includes "SensitiveData:*"
   → Suppresses all sensitive data findings (core Macie purpose defeated)

4. Filter count > 10 per account
   → Suppression sprawl — hard to audit intent

5. No description on a SUPPRESS filter
   → No documentation of why suppression was added
```

## Terraform multi-account example

```hcl
# Administrator account: enable Macie + ASDD
resource "aws_macie2_account" "admin" {
  provider = aws.admin
  status   = "ENABLED"
  finding_publishing_frequency = "FIFTEEN_MINUTES"
}

resource "aws_macie2_organization_admin_account" "admin" {
  provider         = aws.org_management
  admin_account_id = "123456789012"
}

# Auto-enable ASDD for all members
resource "aws_macie2_account" "asdd_config" {
  provider = aws.admin
}

# EventBridge rule for High severity findings
resource "aws_cloudwatch_event_rule" "macie_high" {
  provider      = aws.admin
  name          = "macie-high-severity-finding"
  event_pattern = jsonencode({
    source       = ["aws.macie"]
    "detail-type" = ["Macie Finding"]
    detail       = { severity = ["High"] }
  })
}

resource "aws_cloudwatch_event_target" "lambda" {
  provider = aws.admin
  rule     = aws_cloudwatch_event_rule.macie_high.name
  arn      = aws_lambda_function.macie_remediation.arn
}
```
