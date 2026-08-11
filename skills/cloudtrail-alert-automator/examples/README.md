# End-to-end usage scenario: cloudtrail-alert-automator

A walkthrough showing the skill designing two CloudTrail alert pipelines
for the same account: an AUTOMATION_DEPLOYED root-login alert pipeline
(CRITICAL, never suppressed) and a REVIEW_REQUIRED IAM-change pipeline
where Security Hub is not yet enabled.

## Input (user prompt)

> Design CloudTrail alerting for our AWS account. We need root login
> detection at CRITICAL with full enrichment, and IAM policy change
> detection with Security Hub integration.

```
Design reference: prod-cloudtrail-alerting
Account: 111111111111
Region: us-east-1

CloudTrail: management-events trail, multi-region, enabled.

Alert 1: Root console login
  Severity: CRITICAL
  Suppression: NEVER for root
  Targets: SNS critical, Security Hub, Slack #sec-incidents
  Dedup: 0 minutes

Alert 2: IAM policy changes (AttachRolePolicy, DetachRolePolicy, CreatePolicyVersion)
  Severity: HIGH
  Enrichment: lookup-events 15-min lookback
  Suppression: cicd-deploy-role
  Targets: SNS high, Security Hub, Slack #security
  Dedup: 5 minutes
  Security Hub status: NOT ENABLED
```

## Skill output

```text
ALERT: prod-cloudtrail-alerting
EVENT: ConsoleLogin (by root)
RULE:
  - Pattern: source=aws.signin, userIdentity.type=Root, eventName=ConsoleLogin, responseElements.ConsoleLogin=Success
  - Bus: default
ENRICHMENT:
  - lookup-events: 15-min lookback for root actor context
  - Severity: CRITICAL
ROUTING:
  - SNS: arn:aws:sns:us-east-1:111111111111:cloudtrail-critical
  - Security Hub: finding import configured (CRITICAL, NEW)
  - Slack: webhook configured (#sec-incidents)
DEDUP:
  - Window: 0 (never dedup root login)
  - Key: N/A
SUPPRESSION:
  - Roles: N/A — root events NEVER suppressed
  - Non-suppressible: DeleteTrail, StopLogging, root
VERDICT: AUTOMATION_DEPLOYED
GAP: None
TEMPLATE:
  aws events put-rule --name cloudtrail-alert-root-login --event-pattern '{"source":["aws.signin"],"detail-type":["AWS API Call via CloudTrail"],"detail":{"userIdentity":{"type":["Root"]},"eventName":["ConsoleLogin"],"responseElements":{"ConsoleLogin":["Success"]}}}'

ALERT: prod-cloudtrail-alerting
EVENT: AttachRolePolicy, DetachRolePolicy, CreatePolicyVersion
RULE:
  - Pattern: source=aws.iam, eventName=[AttachRolePolicy, DetachRolePolicy, CreatePolicyVersion]
  - Bus: default
ENRICHMENT:
  - lookup-events: configured, 15-min lookback
  - Severity: HIGH
ROUTING:
  - SNS: arn:aws:sns:us-east-1:111111111111:cloudtrail-high
  - Security Hub: NOT CONFIGURED — securityhub describe-hub returns ResourceNotFoundException
  - Slack: webhook configured (#security)
DEDUP:
  - Window: 5 minutes
  - Key: MD5(eventName|actorArn|resourceId)
SUPPRESSION:
  - Roles: cicd-deploy-role
  - Non-suppressible: DeleteTrail, StopLogging, root
VERDICT: REVIEW_REQUIRED
GAP: Security Hub is not enabled. Steps: (1) aws securityhub enable-security-hub; (2) update enrichment Lambda with BatchImportFindings call; (3) re-deploy Lambda. SNS + Slack are operational.
```

**Account-level aggregate verdict: AUTOMATION_DEPLOYED for root-login
alert + REVIEW_REQUIRED for IAM-change alert.** Deploy the root-login
pipeline immediately; the IAM pipeline requires Security Hub enablement
before full deployment.

## What the skill caught that a generic assistant misses

1. **The ConsoleLogin success filter.** A generic assistant creates a
   rule for `ConsoleLogin` without filtering on
   `responseElements.ConsoleLogin: Success`. The skill always includes
   the filter — without it, a brute-force scenario generates thousands
   of failure alerts per minute, exhausting Lambda concurrency.

2. **The root-event non-suppression rule.** A generic assistant adds
   CI/CD suppression without distinguishing root events. The skill
   never suppresses root login, `DeleteTrail`, or `StopLogging` —
   even for known automation roles.

3. **The dedup window difference.** A generic assistant applies a
   uniform dedup window. The skill uses 0 minutes for root (every login
   independently alerted) and 5 minutes for IAM changes (same actor +
   event within window is deduplicated).

4. **The Security Hub enablement check.** A generic assistant wires
   `BatchImportFindings` without checking whether Security Hub is
   enabled. The skill detects the missing prerequisite and emits
   REVIEW_REQUIRED with the specific enablement step.

5. **The lookup-events enrichment.** A generic assistant sends raw
   CloudTrail events to SNS. The skill enriches every alert with the
   actor's 15-minute API call history via `lookup-events`, providing
   investigative context.

## Slash-command invocation

```
/aws:automate-cloudtrail-alert
```

Or via the orchestrator:

```
/aws:pipeline
You: "design CloudTrail alerting for root login and IAM changes"
```

## CLI routing

```bash
node cli/bin/cli.js route "automate CloudTrail alerts"
# [Phase: Automate | Skills routed: cloudtrail-alert-automator]
```

## Live-account invocation (requires AWS CLI)

```bash
# Verify CloudTrail is logging
aws cloudtrail get-trail-status --name management-events --region us-east-1

# Check existing EventBridge rules for CloudTrail
aws events list-rules --name-prefix cloudtrail-alert --region us-east-1

# Check Security Hub status
aws securityhub describe-hub --region us-east-1

# Check existing SNS topics
aws sns list-topics --region us-east-1

# Verify the enrichment Lambda exists
aws lambda get-function --function-name cloudtrail-alert-enrichment \
  --query 'Configuration.[LastModified,State]' --region us-east-1
```

Then paste the output into the skill for alert pipeline design.
