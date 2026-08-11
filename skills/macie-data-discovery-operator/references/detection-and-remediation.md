# Detection and Remediation Guide — Macie Data Discovery Operator

Deep reference on managed vs custom data identifiers, finding types
and severities, suppression rule patterns, automated ML-based discovery,
Security Hub integration, Lambda / Step Functions remediation workflows,
and cross-account findings aggregation. Loaded on demand by the skill.

## Managed data identifier categories

Macie provides ~150+ managed data identifiers across categories:

### PII (Personally Identifiable Information)

| Identifier | Region | Example |
|---|---|---|
| `USA_SOCIAL_SECURITY_NUMBER` | US | 123-45-6789 |
| `USA_PASSPORT_NUMBER` | US | Passport card / book |
| `USA_DRIVERS_LICENSE_NUMBER` | US | State-specific format |
| `UK_NATIONAL_INSURANCE_NUMBER` | UK | AB123456C |
| `CA_SOCIAL_INSURANCE_NUMBER` | Canada | 123-456-789 |
| `AU_TAX_FILE_NUMBER` | Australia | 123456782 |
| `DE-national-id-number` | Germany | |
| `FRANCE-INSEE-CODE` | France | |

### Financial data

| Identifier | Example |
|---|---|
| `CREDIT_CARD_NUMBER` | 4111-1111-1111-1111 (Luhn-validated) |
| `BANK-ACCOUNT-NUMBER` | Region-specific |
| `SWIFT-CODE` | 8 or 11 chars |
| `IBAN-CODE` | International bank account |

### Credentials and secrets

| Identifier | Example |
|---|---|
| `AWS_ACCESS_KEY_ID` | AKIAIOSFODNN7EXAMPLE |
| `AWS_SECRET_KEY` | (paired with access key) |
| `RSA_PRIVATE_KEY` | -----BEGIN RSA PRIVATE KEY----- |
| `PGP_PRIVATE_KEY` | -----BEGIN PGP PRIVATE KEY BLOCK----- |
| `API_KEY` | Various formats (Stripe, Slack, etc.) |

### Contact data

| Identifier | Example |
|---|---|
| `EMAIL_ADDRESS` | user@example.com |
| `PHONE_NUMBER` | Region-specific |
| `URL` | https://example.com |
| `IP_ADDRESS` | 192.168.1.1 |

### Selector strategies

```bash
# ALL — scan for all 150+ identifiers (comprehensive, expensive)
--managed-data-identifier-selector ALL

# RECOMMENDED — Macie samples content and selects relevant identifiers
--managed-data-identifier-selector RECOMMENDED

# LIST — select specific identifiers (targeted)
--managed-data-identifier-selector-ids \
  USA_SOCIAL_SECURITY_NUMBER CREDIT_CARD_NUMBER EMAIL_ADDRESS
```

## Custom data identifier deep dive

Custom identifiers use regex patterns with proximity-based keyword
matching to reduce false positives.

### Regex rules

- Must be PCRE-compatible.
- Macie scans the full object content, not just filenames.
- Regex with broad patterns (e.g., `[0-9]+`) without keywords generate
  excessive false positives.

### Keyword proximity

Macie only reports a regex match if a keyword appears within
`maximum-match-distance` characters of the match. This is the critical
false-positive filter.

```bash
aws macie2 create-custom-data-identifier \
  --name "employee-id-pattern" \
  --regex "EMP[0-9]{6}" \
  --keywords "employee" "emp_id" "staff" \
  --maximum-match-distance 50 \
  --severity-levels HIGH
```

### Ignore words

Exclude matches containing specific words (test data, examples):

```bash
--ignore-words "example" "test" "sample" "demo"
```

### Common custom identifier patterns

| Use case | Regex | Keywords |
|---|---|---|
| Employee ID | `EMP[0-9]{6}` | employee, emp_id, staff |
| Internal API token | `tk_[a-zA-Z0-9]{32}` | token, api_key, secret |
| Customer account | `ACCT-[0-9]{4}-[0-9]{4}` | account, customer, client |
| Project code | `PRJ-[A-Z]{3}-[0-9]{4}` | project, code |

## Finding types and severity

### Policy findings

| Finding type | Trigger | Severity |
|---|---|---|
| `policy:IAMUser/S3/BucketPublic` | Bucket ACL or policy allows public access | Medium-High |
| `policy:IAMUser/S3/BucketSharedExternally` | Bucket shared with external account | Medium |
| `policy:IAMUser/S3/BucketReplicatedExternally` | Replication config to external account | Medium |

### Sensitive data findings

| Finding type | Trigger | Severity |
|---|---|---|
| `sensitiveData:S3Object/<Identifier>` | Managed identifier matched (e.g., SSN, credit card) | Medium-High |
| `sensitiveData:S3Object/Custom` | Custom data identifier matched | High (configurable) |
| `sensitiveData:S3Object/Multiple` | Multiple identifiers matched in one object | High |

## Suppression rule patterns

Suppression rules auto-archive findings matching criteria:

### Suppress by bucket tag (test environment)

```bash
aws macie2 put-findings-filter \
  --name "suppress-test-env" \
  --action '{archived:true}' \
  --finding-criterion \
    criterion='{resource.tags.tagKey:{eq:[Environment]},resource.tags.tagValue:{eq:[test]}}'
```

### Suppress by finding type (low-severity email)

```bash
aws macie2 put-findings-filter \
  --name "suppress-email-findings" \
  --action '{archived:true}' \
  --finding-criterion \
    criterion='{category:{eq:[sensitiveData:S3Object/EMAIL_ADDRESS]}}'
```

### Suppress by bucket name prefix (known-data buckets)

```bash
aws macie2 put-findings-filter \
  --name "suppress-known-data" \
  --action '{archived:true}' \
  --finding-criterion \
    criterion='{resource.s3Bucket.name:{contains:[known-data]}}'
```

## Automated discovery (ML-based)

```bash
# Enable automated ML-based discovery
aws macie2 update-automated-discovery-configuration \
  --status ENABLED \
  --auto-enable-members true

# Check status
aws macie2 get-automated-discovery-configuration
```

Automated discovery:
- Continuously scans all S3 buckets (no job management needed).
- Uses ML to sample content and select relevant identifiers.
- Detects both managed PII and unusual data patterns.
- Still has scan frequency (not instant) — objects are queued.

## Security Hub integration

```bash
# Enable Security Hub (if not already enabled)
aws securityhub enable-security-hub \
  --enable-default-standards

# Enable Macie → Security Hub integration
aws macie2 put-classification-export-configuration \
  --configuration '{securityHubConfiguration:{enableSecurityHubIntegration:true}}'

# Verify
aws macie2 get-classification-export-configuration
```

Macie findings appear in Security Hub as:
- Product ARN: `arn:aws:securityhub:...:product/amazon/macie`
- Finding type: `Software and Configuration Checks/AWS Macie`
- Severity: mapped from Macie severity (High, Medium, Low)

## Lambda + Step Functions remediation

### EventBridge rule (trigger on high-severity findings)

```bash
aws events put-rule \
  --name "macie-finding-trigger" \
  --event-pattern '{
    "source": ["aws.macie"],
    "detail-type": ["Macie Finding"],
    "detail": {
      "severity": ["High", "Critical"]
    }
  }'
```

### Lambda remediation (single-step)

```python
import json
import boto3

def lambda_handler(event, context):
    finding = json.loads(event['detail'])
    bucket = finding['resource']['s3Bucket']['name']
    key = finding['resource']['s3Object']['key']

    # Quarantine: copy to isolated bucket, delete original
    s3 = boto3.client('s3')
    s3.copy_object(
        Bucket='macie-quarantine',
        Key=f'quarantined/{bucket}/{key}',
        CopySource={'Bucket': bucket, 'Key': key}
    )
    s3.delete_object(Bucket=bucket, Key=key)

    # Restrict bucket ACL (block public access)
    s3.put_public_access_block(
        Bucket=bucket,
        PublicAccessBlockConfiguration={
            'BlockPublicAcls': True,
            'IgnorePublicAcls': True,
            'BlockPublicPolicy': True,
            'RestrictPublicBuckets': True
        }
    )

    # Notify security team
    sns = boto3.client('sns')
    sns.publish(
        TopicArn='arn:aws:sns:us-east-1:123456789012:security-alerts',
        Subject=f'Macie PII Remediation: {bucket}/{key}',
        Message=json.dumps(finding, indent=2)
    )

    return {'statusCode': 200, 'body': 'Remediation complete'}
```

### Step Functions workflow (multi-step)

For complex remediation requiring conditional logic, retries, and
human approval:

```json
{
  "StartAt": "ParseFinding",
  "States": {
    "ParseFinding": {
      "Type": "Pass",
      "Next": "CheckBucketExposure"
    },
    "CheckBucketExposure": {
      "Type": "Task",
      "Resource": "arn:aws:lambda:...:function:check-bucket-acl",
      "Next": "IsPublic?"
    },
    "IsPublic?": {
      "Type": "Choice",
      "Choices": [
        {"Variable": "$.isPublic", "BooleanEquals": true, "Next": "QuarantineObject"}
      ],
      "Default": "LogOnly"
    },
    "QuarantineObject": {
      "Type": "Task",
      "Resource": "arn:aws:lambda:...:function:quarantine-object",
      "Next": "RestrictACL"
    },
    "RestrictACL": {
      "Type": "Task",
      "Resource": "arn:aws:lambda:...:function:restrict-acl",
      "Next": "NotifySecurity"
    },
    "NotifySecurity": {
      "Type": "Task",
      "Resource": "arn:aws:sns:...:security-alerts",
      "End": true
    },
    "LogOnly": {
      "Type": "Pass",
      "End": true
    }
  }
}
```

## Cross-account findings aggregation

```bash
# In delegated admin account: list all member accounts
aws macie2 list-members \
  --query 'members[*].[accountId,relationshipStatus]' --output text

# Query findings across all member accounts
aws macie2 list-findings \
  --finding-criterion \
    criterion='{severity:{eq:[HIGH,CRITICAL]}}' \
  --max-results 100

# Get finding details (includes source account)
aws macie2 get-findings --finding-ids <finding-id-1> <finding-id-2>
```

## AWS documentation references

- Amazon Macie User Guide — https://docs.aws.amazon.com/macie/latest/user/what-is-macie.html
- Managed Data Identifiers — https://docs.aws.amazon.com/macie/latest/user/managed-data-identifiers.html
- Custom Data Identifiers — https://docs.aws.amazon.com/macie/latest/user/custom-data-identifiers.html
- Classification Jobs — https://docs.aws.amazon.com/macie/latest/user/classification-jobs.html
- Macie Findings — https://docs.aws.amazon.com/macie/latest/user/findings.html
- Security Hub Integration — https://docs.aws.amazon.com/macie/latest/user/securityhub-integration.html
- Automated Discovery — https://docs.aws.amazon.com/macie/latest/user/automated-discovery.html
