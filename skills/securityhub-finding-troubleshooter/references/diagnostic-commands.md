# Diagnostic Commands — Security Hub Finding Troubleshooter

> Moved verbatim from SKILL.md for progressive disclosure (agentskills.io). Load on demand.

### Account-wide pre-flight commands

```bash
# Hub, enabled standards, aggregator, administrator
aws securityhub describe-hub --output json
aws securityhub describe-standards --output json
aws securityhub list-enabled-products-for-import --output json
aws securityhub get-finding-aggregator --output json 2>/dev/null || echo "no aggregator"
aws securityhub get-administrator-account --output json 2>/dev/null || echo "no admin"

# The finding itself (preferred path)
aws securityhub get-findings \
  --filters '{"Id":[{"Value":"<finding-id>","Comparison":"EQUALS"}]}' \
  --output json

# Finding statistics by severity and control
aws securityhub get-findings-statistics \
  --filters '{"AwsAccountId":[{"Value":"<acct>","Comparison":"EQUALS"}]}' \
  --statistics-types SEVERITY_COUNT RECORD_STATE_COUNT --output json

# Config rule backing the Security Hub control
aws configservice describe-config-rules \
  --config-rule-names "<rule-name>" --output json
aws configservice describe-configuration-recorders --output json
```

#### Step 2a — Public access block (S3.1 / PCI.S3.1-5)

```bash
# Public Access Block on the account and bucket
aws s3control get-public-access-block --account-id <acct> --output json
aws s3api get-public-access-block --bucket <bucket> --output json

# Bucket policy and ACL for cross-check
aws s3api get-bucket-policy --bucket <bucket> --output json
aws s3api get-bucket-acl --bucket <bucket> --output json
```

#### Step 2b — Bucket encryption (S3.4 / S3.6)

```bash
aws s3api get-bucket-encryption --bucket <bucket> --output json
```

#### Step 2c — Versioning / MFA delete (S3.9 / S3.10)

```bash
aws s3api get-bucket-versioning --bucket <bucket> --output json
```

#### Step 3a — Password policy (CIS.1.5-1.11 / PCI.IAM.1)

```bash
aws iam get-account-password-policy --output json
```

#### Step 3b — MFA on root / IAM users (CIS.1.4 / FSBP.IAM.7)

```bash
aws iam get-account-summary --output json | \
  jq '.SummaryMap | {AccountMFAEnabled, UsersQuota, MFADevicesInUse}'
```

#### Step 3c — Aged access keys (CIS.1.3 / FSBP.IAM.6)

```bash
aws iam get-credential-report --output text --query 'Content' | \
  base64 --decode | awk -F',' 'NR==1 || ($5!="N/A" && $5<"2025-08-10T00:00:00Z") {print}'
```

#### Step 4a — IMDSv2 required (EC2.8 / FSBP.EC2.8)

```bash
aws ec2 describe-instances --instance-ids <i-id> --output json | \
  jq '.Reservations[0].Instances[0].MetadataOptions'
# HttpTokens: optional (bad) / required (good)
```

#### Step 4b — Security group 0.0.0.0/0 (EC2.2 / EC2.4 / PCI.EC2.2-4)

```bash
aws ec2 describe-security-groups --group-ids <sg-id> --output json | \
  jq '.SecurityGroups[].IpPermissions[] | select(.IpRanges[]?.CidrIp=="0.0.0.0/0")'
```

#### Step 5 — KMS key rotation (KMS.3 / PCI.KMS.1)

```bash
aws kms describe-keys --key-ids <key-id> --output json | \
  jq '.Keys[0] | {KeyId, KeyState, EnableKeyRotation, KeyUsage}'
```

#### Step 6 — CloudTrail data events (CloudTrail.4 / CIS.2.7)

```bash
aws cloudtrail describe-trails --output json
aws cloudtrail get-event-selectors --trail-name <trail> --output json
```

#### Step 7 — Config recorder coverage (Config.1)

```bash
aws configservice describe-configuration-recorders --output json
aws configservice describe-delivery-channels --output json
```

#### Step 8 — NOT_AVAILABLE StatusReasons read

```bash
# Read StatusReasons from the finding
jq '.Compliance.StatusReasons' finding.json
# Each entry: {ReasonCode: <code>, Description: <text>}
```

#### Step 9 — Stuck RESOLVED-but-still-appearing

```bash
# Compare Security Hub state vs Config state
aws securityhub get-findings \
  --filters '{"Id":[{"Value":"<id>","Comparison":"EQUALS"}]}' \
  --output json | jq '.Findings[0].Workflow.Status, .Findings[0].Compliance.Status'
aws configservice get-resource-config-history \
  --resource-type <type> --resource-id <id> --output json
```

#### Step 10 — Cross-account aggregation gap

```bash
# From the aggregator (administration) account
aws securityhub get-finding-aggregator --output json
aws securityhub list-members --output json
# From the member account
aws securityhub get-administrator-account --output json
```

#### Step 11 — Custom action wired but not firing

```bash
# EventBridge rule + target + Lambda permission
aws events describe-rule --name <rule> --output json
aws events list-targets-by-rule --rule <rule> --output json
aws lambda get-policy --function-name <fn> --output json
# Test invocation
aws events test-event-pattern --event <json> --event-pattern <json>
```

#### Step 12 — Automation Rules not applying

```bash
# List and inspect Automation Rules (2024 GA feature)
aws securityhub list-automation-rules --output json
aws securityhub get-automation-rules \
  --automation-rules-arn-list '["<arn>"]' --output json
```

