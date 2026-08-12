# End-to-end usage scenario: guardduty-finding-automator

A walkthrough showing the skill designing two GuardDuty automation
workflows for the same account: an AUTOMATION_DEPLOYED EC2 isolation
workflow for a Critical crypto mining finding and a REVIEW_REQUIRED
workflow for a Low-severity recon finding from an authorized scanner.
Demonstrates the severity-based routing matrix and the false-positive
suppression recommendation.

## Input (user prompt)

> Design automated GuardDuty response for our findings. We have crypto
> mining on an EC2 instance (Critical) and port probes from our internal
> scanner (Low). We want both handled automatically.

```
Design reference: prod-guardduty-rollout
Account: 111111111111
Region: us-east-1

Finding 1: CryptoCurrency:EC2/BitcoinTool
  Severity: 9.0 (CRITICAL)
  Resource: i-0compromised789
  Isolation SG: sg-isolation-forensics
  Lambda: guardduty-auto-remediation
  SNS topic: arn:aws:sns:us-east-1:111111111111:guardduty-alerts
  Pre-prod validation: completed (3 sandbox instances tested).

Finding 2: Recon:EC2/PortProbeUnprotectedPort
  Severity: 2.0 (LOW)
  Resource: i-0webfrontend01
  Source IP: 198.51.100.50 (authorized vulnerability scanner)
```

## Skill output

```text
AUTOMATION_DEPLOYED: prod-guardduty-rollout
FINDING_TYPE: CryptoCurrency:EC2/BitcoinTool
SEVERITY: 9.0 (CRITICAL)
ROUTING:
  - EventBridge rule: guardduty-critical-high-routing
  - Filter: severity >= 7.0 (Lambda branches internally on type)
  - Target: Lambda guardduty-auto-remediation (DLQ: guardduty-remediation-dlq)
REMEDIATION:
  - Action: isolate EC2 via SG swap + EBS snapshot + IAM key revoke (unconditional)
  - Lambda: guardduty-auto-remediation
  - Rollback: restore original SGs from DynamoDB (key: instance-id)
NOTIFICATION:
  - SNS topic: arn:aws:sns:us-east-1:111111111111:guardduty-alerts
  - Content: finding type, severity, instance ID, actions taken, rollback instructions
  - Paging: on-call (Critical)
INTEGRATION:
  - Security Hub: custom enriched finding (TTP: Impact — TA0040)
  - CloudTrail correlation: enabled (60-min window, MITRE chain detection)
SAFETY:
  - Finding ID deduplication: DynamoDB table guardduty-processed-findings (7-day TTL)
  - False-positive suppression: N/A (Critical — no suppression)
  - Rate limiting: Lambda reserved concurrency = 10
AUDIT:
  - CloudTrail: ec2:ModifyNetworkInterfaceAttribute, ec2:CreateSnapshot, iam:UpdateAccessKey
  - CloudWatch: /aws/lambda/guardduty-auto-remediation
VERDICT: AUTOMATION_DEPLOYED
GAP: None
TEMPLATE:
  aws events put-rule --name guardduty-critical-high-routing --event-pattern '{"source":["aws.guardduty"],"detail-type":["GuardDuty Finding"],"detail":{"severity":[{"numeric":[">=",7.0]}]}}'

AUTOMATION_DEPLOYED: prod-guardduty-rollout
FINDING_TYPE: Recon:EC2/PortProbeUnprotectedPort
SEVERITY: 2.0 (LOW)
ROUTING:
  - EventBridge rule: none (Low severity — log only tier)
  - Filter: N/A
  - Target: CloudWatch Logs (trend analysis)
REMEDIATION:
  - Action: none (Low — no auto-response)
  - Lambda: N/A
  - Rollback: N/A
NOTIFICATION:
  - SNS topic: N/A (Low severity — no notification)
  - Content: N/A
  - Paging: N/A
INTEGRATION:
  - Security Hub: native forwarding only
  - CloudTrail correlation: enabled (background correlation for trend)
SAFETY:
  - Finding ID deduplication: N/A (no auto-action)
  - False-positive suppression: RECOMMENDED — suppress-authorized-scanner
  - Rate limiting: N/A
AUDIT:
  - CloudTrail: N/A (no auto-action)
  - CloudWatch: GuardDuty finding log
VERDICT: REVIEW_REQUIRED
GAP: Low-severity recon from authorized scanner 198.51.100.50 does not warrant auto-response. Recommend: (1) create suppression filter for authorized scanner IP to reduce alert noise; (2) set up CloudWatch metric for recon trend analysis (spike detection beyond baseline); (3) CloudTrail correlation in background — a recon finding followed by a High finding within 60 min indicates a real attack chain.
TEMPLATE:
  aws guardduty create-filter --detector-id <id> --name suppress-authorized-scanner --action ARCHIVE --finding-criteria '{"Criterion":{"type":{"Eq":["Recon:EC2/PortProbeUnprotectedPort"]},"service.additionalInfo.remoteIpDetails.ipAddressV4":{"Eq":["198.51.100.50"]}}}'
```

**Account-level aggregate verdict: AUTOMATION_DEPLOYED for crypto mining +
REVIEW_REQUIRED for recon.** Deploy the critical response pipeline
immediately; the recon finding needs a suppression filter and trend
analysis, not auto-containment.

## What the skill caught that a generic assistant misses

1. **The severity tier distinction.** A generic assistant wires both
   findings to the same Lambda with the same auto-isolate action. The
   skill refuses — Low-severity findings must not trigger containment;
   they get logged and correlated instead.

2. **The false-positive suppression.** A generic assistant ignores the
   authorized scanner context. The skill recommends a `create-filter`
   suppression for the scanner IP to eliminate alert noise — the most
   common cause of GuardDuty alert fatigue.

3. **The finding ID deduplication.** A generic assistant wires the
   Lambda without deduplication. The skill requires a DynamoDB dedup
   table because GuardDuty updates the same finding ID as evidence
   accumulates, and EventBridge emits on every update.

4. **The unconditional IAM key revocation for Critical.** A generic
   assistant applies the last-used check uniformly. The skill knows
   that for CryptoCurrency/Backdoor findings, the key must be revoked
   unconditionally — the instance is already compromised.

5. **The TTP correlation layer.** A generic assistant treats each
   finding in isolation. The skill adds a CloudTrail correlation
   layer that detects attack chains (Recon → Initial Access →
   Persistence → Exfiltration) via MITRE ATT&CK mapping.

6. **The EventBridge severity serialization gotcha.** A generic
   assistant writes a numeric severity match rule and assumes it
   works. The skill knows the severity field serialization is
   inconsistent across detector versions and recommends routing all
   findings to Lambda with internal branching as a fallback.

## Slash-command invocation

```
/aws:automate-guardduty-finding
```

Or via the orchestrator:

```
/aws:pipeline
You: "automate GuardDuty response for EC2 findings"
```

## CLI routing

```bash
node cli/bin/cli.js route "automate GuardDuty response"
# [Phase: Automate | Skills routed: guardduty-finding-automator]
```

## Live-account invocation (requires AWS CLI)

```bash
# Check GuardDuty detector status
aws guardduty list-detectors --region us-east-1 --profile default

# Get finding statistics by severity
aws guardduty get-findings-statistics \
  --detector-id <detector-id> \
  --statistics-criteria GROUP_BY=severity \
  --region us-east-1 --profile default

# Check existing EventBridge rules for GuardDuty
aws events list-rules \
  --name-prefix guardduty \
  --region us-east-1 --profile default

# Check existing suppression filters
aws guardduty list-filters \
  --detector-id <detector-id> \
  --region us-east-1 --profile default

# Verify Security Hub is enabled
aws securityhub describe-hub \
  --region us-east-1 --profile default

# Check Organizations delegated admin for GuardDuty
aws organizations list-delegated-administrators \
  --service-principal guardduty.amazonaws.com \
  --region us-east-1 --profile default

# Verify Lambda function exists
aws lambda get-function-configuration \
  --function-name guardduty-auto-remediation \
  --region us-east-1 --profile default
```

Then paste the output into the skill for workflow design.
