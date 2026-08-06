# End-to-end usage scenario: macie-data-classification-auditor

A walkthrough showing the skill auditing a Macie posture that has active
coverage but untriaged HIGH-severity findings (SSN, credit card, AWS
credentials), demonstrating the Step 2 UNTRIAGED_FINDINGS verdict,
severity-by-category reasoning, and the credential-first remediation
workflow.

## Input (user prompt)

> Audit our Macie posture before the PCI-DSS compliance review next week.
> We need to make sure all sensitive data findings are addressed.

```yaml
Account: 333333333333, Region: us-east-1

Macie session:
  status: ENABLED

Automated discovery (ASDD):
  status: ENABLED
  lastRunTime: 2026-08-04T14:00:00Z

Classification jobs:
  - jobId: pci-compliance-scan
    name: full-pii-scan
    jobStatus: COMPLETE
    jobType: ONE_TIME
    lastRunTime: 2026-08-04T12:00:00Z
    samplingPercentage: 100
    buckets: [customer-data, app-config]

Findings (open, archived: false):
  - findingId: f-001
    severity: HIGH
    type: SensitiveData:S3Object/Credentials
    archived: false
    resourceName: s3://customer-data/exports/q3-customers.csv
    classificationDetails:
      sensitiveData:
        - category: CREDENTIALS
          detectedDataType: AWS_CREDENTIALS
          count: 1
  - findingId: f-002
    severity: HIGH
    type: SensitiveData:S3Object/Personal
    archived: false
    resourceName: s3://customer-data/exports/q3-customers.csv
    classificationDetails:
      sensitiveData:
        - category: PERSONAL_INFORMATION
          detectedDataType: US_SOCIAL_SECURITY_NUMBER
          count: 45000
  - findingId: f-003
    severity: HIGH
    type: SensitiveData:S3Object/Financial
    archived: false
    resourceName: s3://customer-data/exports/payment-history.csv
    classificationDetails:
      sensitiveData:
        - category: FINANCIAL_INFORMATION
          detectedDataType: CREDIT_CARD_NUMBER
          count: 12000

Allow lists: (none)

Security Hub export: enabled
```

## Skill output

```text
ACCOUNT: 333333333333 (us-east-1)
VERDICT: UNTRIAGED_FINDINGS
REASON: ASDD is enabled and the classification job completed, but 3 open
HIGH-severity findings (AWS_CREDENTIALS, US_SOCIAL_SECURITY_NUMBER,
CREDIT_CARD_NUMBER) have not been triaged (Step 2).
FINDINGS:
  - [UNTRIAGED_FINDINGS] 3 open HIGH findings:
    1 AWS credential finding in s3://customer-data/exports/q3-customers.csv,
    45000 SSN findings in s3://customer-data/exports/q3-customers.csv,
    12000 credit card findings in s3://customer-data/exports/payment-history.csv
    (Step 2)
  - [OK] ASDD enabled with fresh lastRunTime (Step 1)
  - [OK] Classification job COMPLETE with samplingPercentage: 100 (Step 1)
  - [OK] Security Hub export enabled (Step 3a)
REMEDIATION:
  1. CRITICAL PRIORITY — Rotate the exposed AWS credential immediately:
     aws iam list-access-keys --user-name <user>
     aws iam delete-access-key --access-key-id <AKIA...> --user-name <user>
     Then audit CloudTrail for unauthorized API calls using the exposed key.
  2. Investigate SSN findings — verify the 45000 SSNs in
     s3://customer-data/exports/q3-customers.csv are real PII. If so, move
     to an encrypted, access-restricted bucket or delete if no longer needed.
  3. Investigate credit card findings — verify the 12000 credit card numbers
     in s3://customer-data/exports/payment-history.csv. PCI-DSS scope is
     triggered if these are real card numbers.
  4. Archive each finding ONLY AFTER remediation:
     aws macie2 update-findings --finding-ids f-001 f-002 f-003 --status ARCHIVED
```

## What the skill caught that a generic assistant misses

1. **Severity-by-category reasoning.** A generic assistant says "there
   are high findings." The skill identifies the data categories
   (CREDENTIALS, PERSONAL_INFORMATION, FINANCIAL_INFORMATION) and
   explains that severity follows the data type, not the volume. The
   AWS credential finding is prioritized first because it is an immediate
   compromise risk, regardless of count.

2. **The archived-vs-triaged distinction.** A generic assistant may treat
   archived findings as "resolved." The skill explicitly checks
   `archived: false` and flags that these findings have NOT been triaged.
   The archived state is a bookkeeping flag, not a remediation indicator.

3. **PCI-DSS compliance implication.** The skill notes that the credit
   card findings trigger PCI-DSS scope — a non-obvious consequence that
   a compliance auditor would flag but a generalist would miss.

4. **The credential-first remediation ordering.** The skill prioritizes
   the single AWS credential finding over the 45000 SSN findings because
   an exposed access key enables immediate account compromise, while the
   SSN exposure is a data-breach risk but not an active attack vector.

## Slash-command invocation

```
/aws:audit-macie-data-classification
```

Or via the orchestrator:

```
/aws:pipeline
You: "audit our Macie posture before the compliance review"
```

The orchestrator emits
`[Phase: Audit | Skills routed: macie-data-classification-auditor]` and
hands off to this skill for the VERDICT.

## CLI routing

```bash
node cli/bin/cli.js route "audit macie classification coverage"
# [Phase: Audit | Skills routed: macie-data-classification-auditor]
```

## Live-account follow-up (optional, requires AWS CLI)

After remediating the findings, validate the Macie posture:

```bash
# Verify findings are archived
aws macie2 list-findings --query 'findingIds' --output json \
  --findings-filter '{"findingStatus":"ARCHIVED"}' \
  --profile default --region us-east-1

# Confirm ASDD is still running
aws macie2 get-automated-discovery-configuration \
  --profile default --region us-east-1

# Check for any new HIGH findings
aws macie2 list-findings \
  --finding-criteria '{"criterion":{"severity":{"eq":["HIGH"]},"archived":{"eq":[false]}}}' \
  --profile default --region us-east-1

# Verify Security Hub integration is active
aws macie2 get-findings-publication-config \
  --profile default --region us-east-1
```

Then monitor Security Hub for new Macie findings daily during the
compliance review period.
