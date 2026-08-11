# Operating CLI Commands — Macie Data Discovery Operator

Full copy-pasteable CLI command sequence for all Macie operating
steps. Variables to substitute: `<account-id>`, `<region>`, bucket
names, finding IDs, Lambda ARNs, Step Functions ARNs.

## Step 0: Pre-flight checks

```bash
# Confirm caller identity
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
echo "Account: $ACCOUNT_ID"

# Check Macie session status
aws macie2 get-macie-session \
  --query '[status,findingPublishingFrequency]' --output text
# Expect: ENABLED  FIFTEEN_MINUTES

# Check delegated admin (org-level)
aws macie2 get-administrator-account \
  --query 'administrator.accountId' --output text

# List existing classification jobs
aws macie2 list-classification-jobs \
  --query 'items[*].[name,jobStatus,jobType]' --output text

# List member accounts (org-level)
aws macie2 list-members \
  --query 'members[*].[accountId,relationshipStatus]' --output text

# Verify target buckets exist
aws s3api list-buckets \
  --query 'Buckets[?starts_with(Name, `prod`) || starts_with(Name, `financial`)].Name' \
  --output text
```

## Step 1: Enable Macie (standalone)

```bash
aws macie2 enable-macie-session \
  --finding-publishing-frequency FIFTEEN_MINUTES \
  --status ENABLED
```

## Step 1 (org-level): Enable Macie with delegated admin

```bash
# 1. In management account: designate the admin account
aws macie2 enable-organization-admin-account \
  --admin-account-id 123456789012

# 2. In delegated admin account: enable Macie session
aws macie2 enable-macie-session \
  --finding-publishing-frequency FIFTEEN_MINUTES \
  --status ENABLED

# 3. Configure auto-enable for new member accounts
aws macie2 update-organization-configuration \
  --auto-enable true

# 4. Verify org configuration
aws macie2 describe-organization-configuration \
  --query '[autoEnable]' --output text
```

## Step 2: Create a classification job (one-time)

```bash
aws macie2 create-classification-job \
  --name "pii-scan-2026-08" \
  --job-type ONE_TIME \
  --s3-job-definition \
    bucketDefinitions='[{accountId=123456789012,buckets=[sensitive-data-prod]}]' \
  --managed-data-identifier-selector-ids \
    USA_SOCIAL_SECURITY_NUMBER CREDIT_CARD_NUMBER \
  --description "One-time PII scan"
```

## Step 2 (scheduled): Create a daily classification job

```bash
aws macie2 create-classification-job \
  --name "daily-pii-scan" \
  --job-type SCHEDULED \
  --schedule-frequency '{dailySchedule:{}}' \
  --s3-job-definition \
    bucketDefinitions='[{accountId=123456789012,buckets=[prod-data-bucket,financial-records]}]' \
  --managed-data-identifier-selector RECOMMENDED \
  --description "Daily PII scan of production data buckets"
```

## Step 3: Create a custom data identifier

```bash
aws macie2 create-custom-data-identifier \
  --name "employee-id-pattern" \
  --regex "EMP[0-9]{6}" \
  --keywords employee emp_id staff id \
  --ignore-words example test sample demo \
  --maximum-match-distance 50 \
  --severity-levels HIGH \
  --description "Detects EMP###### employee ID format"
```

## Step 4: List and filter findings

```bash
# All high-severity findings in the last 7 days
aws macie2 list-findings \
  --finding-criteria \
    criterion='{severity:{eq:[HIGH]},createdAt:{gte:"2026-08-03T00:00:00Z"}}' \
  --output json

# Get finding details
aws macie2 get-findings \
  --finding-ids <finding-id-1> <finding-id-2>

# Archive a finding (soft delete)
aws macie2 update-findings \
  --finding-ids <finding-id> \
  --status ARCHIVED
```

## Step 5: Create a suppression rule

```bash
aws macie2 put-findings-filter \
  --name "suppress-test-env" \
  --action '{archived:true}' \
  --finding-criterion \
    criterion='{resource.tags.tagKey:{eq:[Environment]},resource.tags.tagValue:{eq:[test]}}' \
  --description "Auto-archive findings on test-environment buckets"
```

## Step 6: Enable automated ML-based discovery

```bash
aws macie2 update-automated-discovery-configuration \
  --status ENABLED \
  --auto-enable-members true

# Verify
aws macie2 get-automated-discovery-configuration \
  --query '[status,autoEnableMembers]' --output text
```

## Step 7: Enable Security Hub integration

```bash
# Enable Security Hub (if not already enabled)
aws securityhub enable-security-hub --enable-default-standards

# Enable Macie → Security Hub
aws macie2 put-classification-export-configuration \
  --configuration '{securityHubConfiguration:{enableSecurityHubIntegration:true}}'

# Verify
aws macie2 get-classification-export-configuration
```

## Step 8: EventBridge rule for remediation

```bash
# Create rule for high-severity Macie findings
aws events put-rule \
  --name "macie-finding-trigger" \
  --event-pattern '{
    "source": ["aws.macie"],
    "detail-type": ["Macie Finding"],
    "detail": {
      "severity": ["High", "Critical"]
    }
  }'

# Add Lambda target
aws events put-targets \
  --rule "macie-finding-trigger" \
  --targets '[{"Id":"macie-remediation-lambda","Arn":"arn:aws:lambda:us-east-1:123456789012:function:macie-remediate"}]'
```

## Step 9: Post-operation verification

```bash
# Verify Macie session
aws macie2 get-macie-session

# Verify classification job status
aws macie2 describe-classification-job --job-id <job-id>

# Verify custom data identifier
aws macie2 get-custom-data-identifier --id <custom-id>

# Verify findings filter
aws macie2 list-findings-filters

# Verify automated discovery
aws macie2 get-automated-discovery-configuration

# Verify Security Hub integration
aws macie2 get-classification-export-configuration

# List recent findings
aws macie2 list-findings \
  --finding-criteria \
    criterion='{createdAt:{gte:"2026-08-09T00:00:00Z"}}' \
  --sort createdAt:desc \
  --max-results 10
```
