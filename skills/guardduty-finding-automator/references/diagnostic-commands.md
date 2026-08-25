# Diagnostic Commands — GuardDuty Finding Automator

Pre-flight command listings moved verbatim from SKILL.md.

## Pre-flight: data requirements — moved from SKILL.md

| Input | Source | Why |
|---|---|---|
| Finding types to automate | `get-findings-statistics --group-by type` | Drives remediation action selection |
| Severity distribution | `get-findings-statistics --group-by severity` | Drives routing tier |
| Sample finding JSON | `get-findings --finding-ids <id>` | Concrete parameters for Lambda |
| EventBridge rule status | `events describe-rule` | Existing routing |
| Lambda function config | `lambda get-function-configuration` | Existing remediation functions |
| Security Hub enabled? | `securityhub describe-hub` | Integration target |
| Organizations delegated admin | `organizations list-delegated-administrators` | Multi-account setup |
| Existing suppression filters | `guardduty list-filters` | Don't overwrite blindly |
| WAF web ACL | `wafv2 list-web-acls` | IP blocking target |
| SNS topic ARN | `sns list-topics` | Notification target |
