# Auto-Remediation Automator — Diagnostic & Verification Commands

Verification and audit command listings moved from SKILL.md.
Load on demand after wiring or executing a remediation.


## Verify a remediation configuration landed (moved from SKILL.md Step 5)

Verify the configuration landed:

```bash
aws configservice describe-remediation-configurations \
  --config-rule-names s3-bucket-public-read-prohibited --output json
```


## Audit and verify a remediation execution (moved from SKILL.md Step 10)

```bash
# 1. SSM execution status
aws configservice describe-remediation-execution-status \
  --config-rule-name s3-bucket-public-read-prohibited \
  --resource-type AWS::S3::Bucket \
  --resource-id my-public-bucket

# 2. Config compliance state after remediation
aws configservice get-compliance-details-by-config-rule \
  --config-rule-name s3-bucket-public-read-prohibited \
  --compliance-types COMPLIANT

# 3. CloudTrail audit trail
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=EventName,AttributeValue=StartAutomationExecution \
  --start-time $(date -v-1H +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date +%Y-%m-%dT%H:%M:%S)

# 4. Config timeline for the resource
aws configservice get-resource-config-history \
  --resource-type AWS::S3::Bucket \
  --resource-id my-public-bucket \
  --limit 5
```
