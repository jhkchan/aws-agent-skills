# Examples: securityhub-remediation-automator

This directory contains end-to-end usage scenarios for the Security Hub
Remediation Automator skill.

## Scenario: Multi-finding remediation rollout

A walkthrough showing the skill designing remediation workflows for two
finding types in the same account: an AUTOMATION_DEPLOYED Critical S3
finding and a REVIEW_REQUIRED custom Lambda credential exposure finding
that requires building a custom fixer.

### Input (user prompt)

> Automate remediation for our Security Hub findings. We have Critical S3
> public access (FSBP S3.1, reversible, runbook available) and a custom
> finding for Lambda environment variable credential exposure (HIGH, no
> managed runbook).

```
Design reference: prod-securityhub-rollout
Account: 111111111111
Region: us-east-1

Finding 1: FSBP S3.1 (S3 public access)
  Severity: CRITICAL
  Sample resource: arn:aws:s3:::app-data-bucket-prod
  Runbook: AWS-DisableS3BucketPublicAccess (managed)
  Pre-prod validation: completed.

Finding 2: Custom/ExposedCredentialsInLambdaEnv
  Severity: HIGH
  Sample resource: arn:aws:lambda:us-east-1:111111111111:function:api-handler
  No managed runbook available.
```

### Skill output

```text
REMEDIATION: prod-securityhub-rollout
FINDING_TYPE: Software and Configuration Checks/AWS Security Best Practices/S3.1
STANDARD: FSBP
SEVERITY_ROUTE: CRITICAL_AUTO
RUNBOOK: AWS-DisableS3BucketPublicAccess
TRIGGER: AUTOMATIC (EventBridge on aws.securityhub, Severity CRITICAL)
SAFETY: post-execution-verification-lambda, cloudtrail-audit, batch-update-findings-on-success
SUPPRESSION: NONE
INSIGHT: arn:aws:securityhub:us-east-1:111111111111:insight/abc123
VERDICT: AUTOMATION_DEPLOYED
GAP: None
TEMPLATE:
  aws events put-rule --name securityhub-critical-auto \
    --event-pattern '{"source":["aws.securityhub"],"detail-type":["Security Hub Findings - Imported"],"detail":{"findings":{"Severity":{"Label":["CRITICAL","HIGH"]},"Workflow":{"Status":["NEW"]}}}}'

REMEDIATION: prod-securityhub-rollout
FINDING_TYPE: Software and Configuration Checks/Custom/ExposedCredentialsInLambdaEnv
STANDARD: Custom
SEVERITY_ROUTE: HIGH_AUTO
RUNBOOK: NONE — no managed runbook for Lambda env-var credential exposure
TRIGGER: NOTIFIED (SNS to security channel)
SAFETY: NONE — workflow not yet built
SUPPRESSION: NONE
INSIGHT: TBD
VERDICT: REVIEW_REQUIRED
GAP: Build a custom Lambda that (1) reads the finding, (2) rotates the credential via Secrets Manager, (3) updates the Lambda environment variable, (4) calls batch-update-findings RESOLVED. Then wire the EventBridge rule.
TEMPLATE: (custom Lambda — see SKILL.md Step 6 pattern)
```

**Account-level aggregate verdict: AUTOMATION_DEPLOYED for S3 +
REVIEW_REQUIRED for custom Lambda finding.** Deploy the S3 workflow
immediately; the custom finding requires building and testing the
Lambda fixer before wiring.

## Slash-command invocation

```
/aws:automate-securityhub-remediation
```

Or via the orchestrator:

```
/aws:pipeline
You: "automate Security Hub remediation for CRITICAL findings"
```

## Live-account invocation (requires AWS CLI)

```bash
# Check enabled standards
aws securityhub get-enabled-standards --region us-east-1 --profile default

# List active findings by severity
aws securityhub get-findings \
  --filters '{"SeverityLabel":[{"Value":"CRITICAL","Comparison":"EQUALS"}]}' \
  --region us-east-1 --profile default

# Check existing EventBridge rules on Security Hub
aws events list-rules --event-bus-name default --region us-east-1 --profile default

# Verify delegated administrator
aws securityhub list-organization-admin-accounts --region us-east-1 --profile default
```
