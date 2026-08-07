---
name: incident-response-automator
description: 'Designs and implements automated AWS incident response workflows across detection (GuardDuty, Security Hub, CloudWatch alarms, EventBridge, AWS Health) and response patterns (EC2 quarantine
  SG, IAM credential revocation, EBS forensic snapshot, memory capture via SSM, WAF/NACL IP block, secret rotation, session revoke), notification (SNS/Slack/Teams via Lambda, on-call paging), and recovery
  (restore from backup, clean AMI redeploy). Orchestrates via EventBridge rule (GuardDuty severity >= 7) to Step Functions state machine (isolate -> snapshot -> notify -> human approval -> recover), SSM
  Automation documents (AWS-IsolateEC2Instance, AWS-DisableIAMUserAccessKey, AWS-RevokeSession), and Systems Manager Incident Manager (response plan with chat channel, on-call). Enforces safety: kill-switch
  required, isolated-account testing, manual override, full CloudTrail + Step Functions audit. Emits deterministic verdict AUTOMATED with response plan or MANUAL_STEP_REQUIRED with specific gap. Use when
  designing IR playbooks or wiring GuardDuty or Security Hub to remediation.'
version: 0.1.0
author: Jacky Chan — AWS Community Builder
license: Apache-2.0
compatibility: Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). No AWS CLI required for offline plan authoring. Live deployment uses aws guardduty list-detectors/create-filter,
  aws events put-rule, aws stepfunctions create-state-machine, aws ssm create-document, aws ssm-incidents create-response-plan, aws iam update-access-key / delete-role-policy, aws ec2 modify-instance-attribute,
  aws ssm start-automation-execution. Requires AWS CLI v2 with guardduty, ssm, ssm-incidents, stepfunctions, events, iam, ec2, and secretsmanager access (SSO or key-based).
keywords:
- incident response
- GuardDuty
- Security Hub
- CloudWatch alarm
- EventBridge
- AWS Health
- Step Functions
- SSM Automation
- Systems Manager
- Incident Manager
- response plan
- EC2 quarantine
- IAM credential revocation
- EBS snapshot
- forensic preservation
- WAF block
- secret rotation
- revoke session
- SNS notification
- Lambda
- kill-switch
- automated remediation
tags:
- security
- incident-response
- automation
- guardduty
- securityhub
- ssm
- stepfunctions
- eventbridge
- incident-manager
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: true
  phase: 4
  supports_pipeline: true
  entry_point: false
  family: Security
  task_type: automate
  skill_class: capability
  lifecycle_status: active
  verdict_shape: AUTOMATED | MANUAL_STEP_REQUIRED
  when_to_use: Designing an automated incident response workflow for AWS, wiring GuardDuty or Security Hub findings to automated containment actions, building a Step Functions state machine that orchestrates
    isolate- snapshot-notify-recover, creating SSM Automation documents for containment (quarantine SG, IAM key revoke, session revoke), standing up an Incident Manager response plan with chat channel and
    on-call engagement, or hardening an existing IR automation with kill-switch and manual override.
  when_not_to_use:
  - Manual incident triage — this skill designs automation; use a triage skill for human-driven investigation.
  - AWS Config rule remediation (different mechanism — uses SSM Automation but triggered by Config non-compliance, not a finding).
  - Disaster recovery (DR) orchestration — DR is about service continuity, not threat containment; use a DR/backup-restore skill.
  - Patch management at scale — use SSM Patch Manager, not IR automation.
  activation_triggers:
  - automate incident response
  - GuardDuty to Lambda remediation
  - Step Functions for incident response
  - EC2 quarantine security group
  - revoke IAM access key automatically
  - forensic EBS snapshot
  - SSM Automation document for containment
  - Incident Manager response plan
  - EventBridge rule for GuardDuty finding
  - kill-switch for IR automation
  - automated WAF block on attacker IP
  invocation_schema:
    type: object
    required:
    - finding_source
    - response_scope
    properties:
      finding_source:
        type: enum
        enum:
        - guardduty
        - securityhub
        - cloudwatch-alarm
        - eventbridge
        - health
        description: The detection source that triggers the workflow.
      response_scope:
        type: enum
        enum:
        - isolate
        - snapshot
        - contain
        - notify
        - recover
        - full-playbook
        description: Which response phases to automate.
      severity_threshold:
        type: number
        description: Minimum finding severity (GuardDuty scale 0-10, Security Hub normalized to 0-100). Default 7.0 (GuardDuty) / 70 (SH).
      existing_workflow:
        type: object
        description: An existing EventBridge rule + Step Functions state machine definition (Amazon States Language JSON). When provided, the skill runs the safety + audit gate and emits AUTOMATED or MANUAL_STEP_REQUIRED.
    output: 'Deterministic block: FINDING_SOURCE / RESPONSE_SCOPE / VERDICT / WORKFLOW / SAFETY / AUDIT / FINDINGS / REMEDIATION. VERDICT is one of AUTOMATED | MANUAL_STEP_REQUIRED. AUTOMATED means the
      workflow is complete, includes a kill-switch, has been validated in an isolated test account, and covers audit logging. MANUAL_STEP_REQUIRED means one or more safety/coverage gates failed — the output
      enumerates the specific gap and the required manual fix.'
---

# Incident Response Automator

## What this skill does

Designs automated AWS incident response workflows that move a compromised
resource from detection to containment without human latency. The skill
supports five detection sources (GuardDuty, Security Hub, CloudWatch
alarms, EventBridge custom events, AWS Health events), five response
patterns (isolate, forensically preserve, contain, notify, recover), and
three orchestration surfaces (EventBridge + Step Functions, SSM Automation
documents, Systems Manager Incident Manager).

The verdict is binary: **AUTOMATED** when the workflow is complete,
includes a kill-switch, has been validated in an isolated test account,
and covers audit logging; **MANUAL_STEP_REQUIRED** when any safety or
coverage gate fails, with the specific gap enumerated in FINDINGS.

## Quick navigation

| # | Section | Jump when |
|---|---|---|
| 1 | [Pre-flight gate](#pre-flight-ir-spec-gate) | Starting any new workflow — blocks unsafe specs |
| 2 | [Decision tree](#decision-tree--workflow-selection) | Picking the right orchestration surface |
| 3 | [Detection sources](#detection-sources) | GuardDuty / Security Hub / CloudWatch / EventBridge / Health |
| 4 | [Response patterns](#response-patterns) | Isolate / Snapshot / Contain / Notify / Recover |
| 5 | [Step Functions orchestration](#step-functions-orchestration) | The state machine that ties it all together |
| 6 | [SSM Automation](#ssm-automation-documents) | Pre-built documents for containment |
| 7 | [Incident Manager](#systems-manager-incident-manager) | Response plans with chat + on-call |
| 8 | [Safety & kill-switch](#safety--kill-switch-mandatory) | The non-negotiable safety baseline |
| 9 | [Audit logging](#audit-logging) | CloudTrail, Step Functions execution history, SSM outputs |
| 10 | [Output format](#output-format-per-workflow) | The exact VERDICT block the skill emits |
| 11 | [NEVER anti-patterns](#never-these-things) | The hardcoded list of IR-automation taboos |
| 12 | [Recent AWS features](#recent-aws-features-2024-2026) | What changed in GuardDuty/SH/Incident Manager in 24 months |

## Mindset

**One-line takeaway:** automated incident response trades latency for
blast radius — a fast wrong action is worse than a slow right one. The
workflow's job is to reduce attacker dwell time; the safety gate's job is
to ensure the automation does not amplify the damage.

Three facts shape every IR automation decision:

- **Detection-to-action latency is the metric that matters.** GuardDuty
  finds an EC2 instance probing internal ports. The mean time to
  containment (MTTC) is the time between GuardDuty emitting the finding
  and the instance being moved to a quarantine security group. Manual MTTC
  is hours (analyst sees alert, investigates, runs CLI). Automated MTTC is
  seconds. But automated MTTC is irrelevant if the workflow also quarantines
  the CEO's laptop during a false positive. Speed requires precision.

- **Containment is reversible; destruction is not.** Moving an EC2 instance
  to a quarantine SG is reversible (move it back). Disabling an IAM access
  key is reversible (re-enable). Deleting the IAM user is NOT reversible
  (history is lost, forensics are harder). Auto-deletion of any resource
  during incident response is forbidden — capture state, contain, and
  escalate to a human for the destructive action.

- **The kill-switch is more important than the trigger.** A workflow that
  fires on every GuardDuty finding of severity >= 7 is fine if it is
  correctly scoped. The same workflow without a kill-switch is an outage
  waiting to happen — a misconfigured detector, a false-positive storm, or
  a planned red-team exercise can trigger hundreds of containment actions
  per minute. The kill-switch MUST be a one-command disable: a feature
  flag on a Parameter Store value, a kill-switch Lambda that the EventBridge
  rule checks first, or a Step Functions `Choice` state that reads a flag.

## Pre-flight: IR spec gate (run before generation)

Validate the input specification before producing any workflow. Several
requirements block generation — proceeding with an invalid spec produces
an unsafe workflow that may amplify damage during a real incident.

| Attribute | Required | Effect on plan |
|---|---|---|
| `finding_source` | YES | Determines the EventBridge event pattern |
| `response_scope` | YES | Determines the actions (isolate only, full-playbook, etc.) |
| `severity_threshold` | Recommended | Default 7.0 (GuardDuty) / 70 (SH). Too low = false-positive storm; too high = miss real incidents |
| `existing_workflow` | For validation mode | When provided, skip generation and run safety + audit gates |
| `test_account_id` | Recommended | Required for the isolated-account test gate |
| `kill_switch_type` | RECOMMENDED | parameter-store / lambda-choice / eventbridge-disable. Default: parameter-store |

**If the spec is incomplete** (missing finding_source or response_scope), output:

```text
FINDING_SOURCE: <unknown>
RESPONSE_SCOPE: <unknown>
VERDICT: MANUAL_STEP_REQUIRED
REASON: Spec is missing required fields (<list>). Cannot generate a
complete workflow without <field>.
REQUIRED:
  - finding_source (guardduty | securityhub | cloudwatch-alarm | eventbridge | health)
  - response_scope (isolate | snapshot | contain | notify | recover | full-playbook)
REMEDIATION: Provide both finding_source and response_scope. Example:
  "automate EC2 quarantine on GuardDuty severity >= 7" maps to
  finding_source=guardduty, response_scope=isolate, severity_threshold=7.0.
```

**Live-account pre-flight checks (skip for offline authoring):**
1. Verify GuardDuty detector is enabled: `aws guardduty list-detectors --query 'DetectorIds'`.
2. Verify Security Hub is enabled: `aws securityhub get-enabled-standards`.
3. Verify EventBridge and Step Functions IAM roles exist (or are in the
   template to be created).
4. Verify SSM Automation service-linked role exists:
   `aws iam get-role --role-name AWSServiceRoleForSSM`.
5. Verify Incident Manager is available in the region (not all regions
   support it — check the AWS regional services list).

## Decision tree — workflow selection

Apply top-to-bottom. First matching rule wins.

```
START
  │
  ├─ response_scope = isolate only? ─────────► SSM Automation document
  │                                              └─ AWS-IsolateEC2Instance or AWS-DisableIAMUserAccessKey (managed)
  │
  ├─ response_scope = single-phase + simple? ──► EventBridge rule + Lambda directly
  │                                              └─ Good for: WAF block IP, revoke single IAM key
  │
  ├─ response_scope = full-playbook? ──────────► EventBridge rule + Step Functions
  │                                              └─ Required when: multiple phases, parallel actions,
  │                                                 human approval gate, error-handling retries
  │
  ├─ need chat channel + on-call engagement? ──► Add Systems Manager Incident Manager
  │                                              └─ Layer on top of EventBridge/Step Functions
  │
  └─ (unrecognized scope) ─────────────────────► MANUAL_STEP_REQUIRED with mapping hint
```

**Orchestration surface selection:**
- **Lambda-only:** for single-action responses that complete in <15 minutes
  (Lambda max). Example: disable one IAM key, block one IP in WAF.
- **Step Functions:** for multi-phase, parallel, or human-approval-gated
  responses. Example: EC2 isolation + EBS snapshot + SNS notification +
  wait for approval + recovery. Step Functions supports up to 1-year
  executions.
- **SSM Automation:** for AWS-curated playbooks with built-in error
  handling. Use managed documents when available; write custom when not.
- **Incident Manager:** when human coordination is core to the response
  (chat channel, on-call page, post-incident timeline). Always layer on
  top of an automated workflow — Incident Manager coordinates humans, it
  does not contain resources.

## Step 0: Expert knowledge — non-obvious IR behaviors

These behaviors change the generated workflow if ignored:

- **GuardDuty finding severity is on a 0-10 scale; Security Hub is 0-100.** A GuardDuty severity 7.0 corresponds to Security Hub severity 70. EventBridge event patterns must use the correct scale — a pattern filtering `Severity: [ { Numeric: [ ">=", 7 ] } ]` works for GuardDuty but catches nothing from Security Hub (which uses 0-100). Always check `source` field: `aws.guardduty` vs `aws.securityhub`.

- **EC2 quarantine via security group works only if the instance is in a VPC with the quarantine SG pre-provisioned.** `AWS-IsolateEC2Instance` swaps the instance's SGs to a pre-created quarantine SG ID. If the quarantine SG does not exist, the automation fails silently (the SSM document errors but the finding remains). Pre-provision the quarantine SG in every VPC where IR automation runs.

- **`update-access-key --status Inactive` revokes the key but does NOT invalidate active sessions.** The IAM user's existing STS sessions continue until they expire (up to 12 hours by default, up to 36 hours with role chaining). To kill active sessions, also call `aws iam put-user-policy` with an explicit Deny on all actions — this forces session re-evaluation and effectively ends them within minutes. SSM document `AWS-RevokeSession` automates this.

- **EBS snapshots are point-in-time, not live.** A snapshot of a running EC2 instance's EBS volume captures the disk state at the moment the snapshot starts. If the attacker is currently writing to disk, those writes may or may not be captured. For forensic integrity, snapshot FIRST (capture state), then isolate (stop writes). Reversing the order loses evidence.

- **Memory capture requires SSM Run Command, not EBS snapshot.** EBS captures disk; it does not capture RAM. Live malware often lives only in memory (fileless). Use `aws ssm send-command` with `AWS-RunPowerShellScript` (Windows) or a custom document (Linux) to dump memory to an S3 bucket BEFORE isolating the instance.

- **GuardDuty Runtime Monitoring (ECS/EKS) (2024-2025) detects container-level threats.** Findings have a `Resource.EksClusterDetails` or `Resource.EcsClusterDetails` block. Containment for container findings is different from EC2 — you cannot "quarantine SG" a running task. The correct containment for ECS is task stop + task definition revert; for EKS it is pod eviction + network policy. Verify the finding type before generating containment actions.

- **EventBridge event patterns support `exists` and `prefix` filters.** A common mistake: filtering only on `detail.type` and missing the `detail.severity` field. Use a `Numeric` comparison on severity to avoid triggering on informational findings. Always include `detail.service.serviceName` to scope to one detector (multi-account aggregations have multiple detectors).

- **Step Functions `Wait` state for human approval can run up to 1 year.** But the Step Functions console shows "Running" the entire time, cluttering the dashboard. Use a `Task` state with `Resource: arn:aws:states:::sqs:sendMessage.waitForTaskToken` for a callback pattern — the workflow pauses until a human approves via an SQS message, instead of polling on a fixed timer.

- **Lambda execution role for IR actions needs cross-service IAM.** A Lambda that calls `ec2:ModifyInstanceAttribute` AND `iam:UpdateAccessKey` AND `sns:Publish` needs all three permissions. Operators often grant only one and the workflow fails on the second action. Use the IAM Policy Simulator with the specific action sequence to verify.

- **SNS subscription must be confirmed before notifications flow.** A new SNS topic with an email or HTTPS subscription does not deliver until the endpoint confirms. A common IR automation failure: incidents happen, SNS fires, but nobody receives the page because the subscription was never confirmed. Always send a test message after creating the topic.

- **Slack/Teams notifications require an incoming webhook URL or a Lambda with the Slack API token.** SNS does not natively post to Slack. The pattern: SNS topic -> Lambda subscription -> Lambda formats and POSTs to the Slack/Teams webhook. Store the webhook URL in Parameter Store (or Secrets Manager for tokens) — never hardcode in the Lambda.

- **AWS Health events for security are NOT the same as GuardDuty findings.** Health events cover account-level issues (compromised root credentials, exposed access keys detected by AWS). They do NOT cover resource-level threats (malicious EC2, anomalous API calls). Use Health for account-level incidents; GuardDuty for resource-level.

- **`aws ssm-incidents start-incident` creates an incident record but does NOT take containment actions.** Incident Manager coordinates the response (chat channel, timeline, runbook steps). To actually contain, wire Incident Manager to a Step Functions execution or SSM Automation via the response plan's `action` members.

- **CloudTrail logs delivery latency is 3-15 minutes.** A workflow that triggers on a CloudTrail API call via EventBridge has built-in 3-15 min latency. For near-real-time detection, use GuardDuty / Security Hub / CloudWatch alarms — these have their own delivery paths (GuardDuty ~5 min, Security Hub ~5-30 min).

- **Cross-account containment requires a hub-and-spoke IAM role.** A Lambda in the security (audit) account cannot directly call `ec2:ModifyInstanceAttribute` in a member account. The pattern: deploy an `IncidentResponseRole` in every member account with a trust policy allowing the security account's Lambda role to assume it. The Lambda assumes the member role, then runs the containment action.

- **SSM Automation documents have a hard 1-hour default timeout per step.** Long-running steps (large EBS snapshot, slow memory dump) silently fail at 1 hour. Override with `"TimeoutSeconds": 3600` maximum, or split into chunks. For memory dumps >1h, use multiple snapshots or a custom SSM document with chunked execution.

- **`aws ssm create-association` on the Quarantine SG association is NOT instant.** SSM association execution has its own schedule (rate-based or cron). For immediate containment, use `aws ssm start-automation-execution` (one-shot) instead of `create-association` (scheduled).

- **GuardDuty finding `id` is unique per finding, but `service.action.additionalInfo` contains the API calls that triggered it.** The finding ID alone is not enough context — include the full `service.action` block in the IR ticket / Slack message so responders know what happened.

## Detection sources

### GuardDuty (preferred for resource-level threats)

```bash
# Verify detector is enabled
aws guardduty list-detectors --query 'DetectorIds'

# Create a filter for high-severity findings
aws guardduty create-filter \
  --detector-id <id> \
  --name high-severity-only \
  --finding-criteria '{"Criterion": {"severity": {"Gte": 7}}}'
```

**EventBridge event pattern for GuardDuty severity >= 7:**

```json
{
  "source": ["aws.guardduty"],
  "detail-type": ["GuardDuty Finding"],
  "detail": {
    "severity": [{"numeric": [">=", 7]}],
    "service.serviceName": ["guardduty"]
  }
}
```

**Finding types worth automating on:**
- `UnauthorizedAccess:EC2/SSHBruteForce` — auto-block source IP in WAF/NACL.
- `UnauthorizedAccess:EC2/RDPBruteForce` — auto-block source IP.
- `Impact:EC2/PortSweep` — quarantine the EC2 instance (it is compromised).
- `CredentialAccess:IAMUser/AnomalousBehavior` — revoke IAM credentials.
- `Trojan:EC2/SSHBruteForce` or `Trojan:EC2/DGADomainRequest` — isolate.
- `Persistence:IAMUser/BackdoorUser` — revoke + investigate.

### Security Hub (preferred for aggregated multi-detector findings)

```json
{
  "source": ["aws.securityhub"],
  "detail-type": ["Security Hub Findings - Imported"],
  "detail": {
    "findings": {
      "Severity": {
        "Label": ["CRITICAL", "HIGH"]
      },
      "Types": [{
        "prefix": ["TTPs/"]
      }]
    }
  }
}
```

**Custom actions:** Security Hub supports custom actions triggered from
the console or API. Wire a custom action to an EventBridge rule for
analyst-initiated containment (no auto-trigger).

### CloudWatch alarms

```json
{
  "source": ["aws.cloudwatch"],
  "detail-type": ["CloudWatch Alarm State Change"],
  "detail": {
    "stateName": ["ALARM"],
    "previousState": { "value": ["OK"] }
  }
}
```

Use for threshold-based detection: anomalous API call volume, unusual
egress traffic, spike in failed logins.

### EventBridge custom events

For application-level signals that do not map to a GuardDuty or Security
Hub finding type: a custom event from a Lambda or ECS task indicating
"detected malicious input" or "container exited with security signal."

### AWS Health events

```json
{
  "source": ["aws.health"],
  "detail-type": ["AWS Health Event"],
  "detail": {
    "service": ["iam"],
    "eventTypeCategory": ["issue", "accountNotification"]
  }
}
```

Use for AWS-detected account-level incidents (exposed access keys,
compromised root credentials).

## Response patterns

### 1. Isolate compromised resource

**EC2 instance quarantine via security group:**

```bash
# Pre-provision the quarantine SG (one-time per VPC)
QUARANTINE_SG=$(aws ec2 create-security-group \
  --group-name quarantine-sg \
  --description "Isolated instances under investigation - no inbound, no outbound" \
  --vpc-id <vpc-id> --query 'GroupId' --output text)

# Strip ALL inbound and outbound rules (deny-all)
aws ec2 revoke-security-group-ingress --group-id $QUARANTINE_SG --ip-permissions $(...)
aws ec2 revoke-security-group-egress --group-id $QUARANTINE_SG --ip-permissions [...]

# Add a single deny-all egress (SG default is allow-all-egress)
aws ec2 authorize-security-group-egress \
  --group-id $QUARANTINE_SG \
  --ip-permissions '[{"IpProtocol":"-1","IpRanges":[{"CidrIp":"0.0.0.0/0"}]}]'

# Wait, the above ADDS allow-all. Revoke it instead:
aws ec2 revoke-security-group-egress --group-id $QUARANTINE_SG \
  --ip-permissions '[{"IpProtocol":"-1","IpRanges":[{"CidrIp":"0.0.0.0/0"}]}]'
# Now the SG has NO egress rules - effectively a deny-all.
```

**OR use the SSM managed document:**

```bash
aws ssm start-automation-execution \
  --document-name AWS-IsolateEC2Instance \
  --document-version 1 \
  --parameters "InstanceId=i-0abc12345,SubnetId=subnet-xxx"
```

`AWS-IsolateEC2Instance` moves the instance to a quarantine VPC subnet
where it can be investigated but cannot reach the internet or other
internal resources.

**IAM credential revocation:**

```bash
# Deactivate the access key
aws iam update-access-key \
  --user-name <user> \
  --access-key-id <AKIA...> \
  --status Inactive

# Revoke active sessions (forces re-auth, killing existing STS sessions)
aws iam put-user-policy \
  --user-name <user> \
  --policy-name RevokeSessions \
  --policy-document '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Deny",
      "Action": "*",
      "Resource": "*"
    }]
  }'

# OR use the SSM managed document (one-shot):
aws ssm start-automation-execution \
  --document-name AWS-RevokeSession \
  --parameters "RoleName=<role>"
```

**EKS pod isolation (2024-2025 — Runtime Monitoring):**

EKS pods cannot be "isolated via SG" directly. Use a network policy to
deny all egress from the compromised pod, or evict the pod and revert
the deployment. Calico or Cilium network policies provide the deny-all
mechanism.

### 2. Forensic preservation

**EBS snapshot for disk forensics:**

```bash
# Snapshot ALL volumes attached to the instance (not just root)
VOLUME_IDS=$(aws ec2 describe-instances --instance-ids i-0abc12345 \
  --query 'Reservations[0].Instances[0].BlockDeviceMappings[*].Ebs.VolumeId' \
  --output text)

for VOL in $VOLUME_IDS; do
  aws ec2 create-snapshot \
    --volume-id $VOL \
    --description "Forensic snapshot $(date -u +%Y-%m-%dT%H:%M:%SZ) - $VOL" \
    --tag-specifications "ResourceType=snapshot,Tags=[{Key=IncidentId,Value=<id>},{Key=Preserve,Value=true}]"
done
```

**Memory capture via SSM Run Command (Linux):**

```bash
# Requires the SSM agent and a memory-capture utility (e.g., LiME)
aws ssm send-command \
  --document-name "AWS-RunShellScript" \
  --instance-ids i-0abc12345 \
  --parameters 'commands=["insmod lime.ko \"path=/tmp/mem.lime format=lime\"", "aws s3 cp /tmp/mem.lime s3://forensic-bucket/<incident-id>/"]' \
  --comment "Memory capture for incident <id>"
```

**Preserve CloudTrail / Lake data:**

```bash
# Export relevant CloudTrail events to S3 for the investigation window
aws cloudtrail lookup-events \
  --start-time 2026-08-01T00:00:00Z \
  --end-time 2026-08-05T00:00:00Z \
  --attribute-key EventName --attribute-value AssumeRole \
  --output json > /tmp/incident-events.json

# For long windows, use Athena on the CloudTrail S3 bucket or CloudTrail Lake.
```

### 3. Containment (block attacker)

**Block source IP in WAF:**

```bash
# Add the attacker IP to an IP set
aws wafv2 update-ip-set \
  --ip-set-id <id> \
  --scope REGIONAL \
  --addresses "$(jq -r '.detail.service.action.remoteIpDetails.ipAddressV4' <event>)/32" \
  --lock-token <token>
```

**Block source IP in NACL (immediate, VPC-scoped):**

```bash
# Add a DENY rule for the source IP at the top of the NACL
aws ec2 create-network-acl-entry \
  --network-acl-id <acl-id> \
  --rule-number 10 \
  --protocol "-1" \
  --rule-action deny \
  --cidr-block <source-ip>/32 \
  --port-range From=0,To=65535
```

**Rotate exposed secrets:**

```bash
# Force immediate rotation
aws secretsmanager rotate-secret \
  --secret-id <arn> \
  --rotation-rule-type IMMEDIATE

# If rotation Lambda is broken, manually update the secret value
aws secretsmanager put-secret-value \
  --secret-id <arn> \
  --secret-string '<new-value>'
```

### 4. Notification

**SNS -> Lambda -> Slack:**

```python
# Lambda subscribed to SNS, posts to Slack incoming webhook
import json, urllib.request, os

def lambda_handler(event, context):
    webhook = os.environ['SLACK_WEBHOOK_URL']  # from Parameter Store
    finding = json.loads(event['Records'][0]['Sns']['Message'])
    msg = {
        'text': f":rotating_light: *IR Alert* — {finding['title']}\n"
                f"Severity: {finding['severity']}\n"
                f"Resource: {finding['resource']}\n"
                f"Finding ID: {finding['id']}"
    }
    urllib.request.urlopen(
        urllib.request.Request(webhook, json.dumps(msg).encode(), {'Content-Type': 'application/json'})
    )
```

**EventBridge -> SNS for paging (e.g., PagerDuty via SNS webhook):**

```bash
# EventBridge rule -> SNS topic -> PagerDuty SNS integration
aws sns subscribe \
  --topic-arn <arn> \
  --protocol https \
  --notification-endpoint https://events.pagerduty.com/integration/.../enqueue
```

**Create Jira ticket via Lambda:**

Lambda calls Jira REST API with finding details. Store Jira API token in
Secrets Manager; never hardcode.

### 5. Recovery

**Restore RDS from point-in-time:**

```bash
aws rds restore-db-instance-to-point-in-time \
  --source-db-instance-identifier <compromised-db> \
  --target-db-instance-identifier <compromised-db-recovered \
  --restore-time 2026-08-04T12:00:00Z \
  --no-deletion-protection
```

**Redeploy from clean AMI:**

```bash
# Launch a fresh instance from a known-good AMI (from the golden AMI pipeline)
aws ec2 run-instances \
  --image-id <clean-ami> \
  --instance-type <type> \
  --subnet-id <subnet> \
  --security-group-ids <prod-sg> \
  --tag-specifications "ResourceType=instance,Tags=[{Key=RestoredFrom,Value=<incident-id>}]"
```

**Verify integrity post-recovery:**

```bash
# Verify file hashes against known-good baseline
aws ssm send-command \
  --document-name AWS-RunShellScript \
  --instance-ids <restored-id> \
  --parameters 'commands=["sha256sum /usr/bin/* /opt/app/bin/* | diff - baseline.txt"]'
```

## Step Functions orchestration

For full-playbook IR (multi-phase, parallel, human-approval), use Step
Functions. The state machine below orchestrates the canonical pattern:

```json
{
  "Comment": "Incident Response: detect -> isolate -> snapshot -> notify -> wait -> recover",
  "StartAt": "CheckKillSwitch",
  "States": {
    "CheckKillSwitch": {
      "Comment": "Read kill-switch from Parameter Store; abort if disabled",
      "Type": "Task",
      "Resource": "arn:aws:states:::ssm:get-parameter",
      "Parameters": {
        "Name": "/ir/kill-switch"
      },
      "Next": "KillSwitchChoice"
    },
    "KillSwitchChoice": {
      "Type": "Choice",
      "Choices": [{
        "Variable": "$.Parameter.Value",
        "StringEquals": "disabled",
        "Next": "AbortWorkflow"
      }],
      "Default": "ParseFinding"
    },
    "AbortWorkflow": {
      "Type": "Succeed",
      "Comment": "Kill-switch tripped — no actions taken"
    },
    "ParseFinding": {
      "Type": "Task",
      "Resource": "arn:aws:lambda:<region>:<account>:function:ir-parse-finding",
      "Next": "ParallelResponse"
    },
    "ParallelResponse": {
      "Type": "Parallel",
      "Next": "NotifyComplete",
      "Branches": [
        {
          "StartAt": "IsolateEC2",
          "States": {
            "IsolateEC2": {
              "Type": "Task",
              "Resource": "arn:aws:states:::ssm:start-automation-execution:waitForTaskToken",
              "Parameters": {
                "DocumentName": "AWS-IsolateEC2Instance",
                "Parameters": {
                  "InstanceId.$": "$.instanceId"
                }
              },
              "End": true
            }
          }
        },
        {
          "StartAt": "SnapshotVolumes",
          "States": {
            "SnapshotVolumes": {
              "Type": "Task",
              "Resource": "arn:aws:lambda:<region>:<account>:function:ir-snapshot-volumes",
              "End": true
            }
          }
        },
        {
          "StartAt": "NotifySlack",
          "States": {
            "NotifySlack": {
              "Type": "Task",
              "Resource": "arn:aws:lambda:<region>:<account>:function:ir-notify-slack",
              "End": true
            }
          }
        }
      ]
    },
    "NotifyComplete": {
      "Type": "Task",
      "Resource": "arn:aws:sns:<region>:<account>:ir-notifications",
      "Next": "WaitForHumanApproval"
    },
    "WaitForHumanApproval": {
      "Comment": "Human callback via SQS + task token — no fixed timeout",
      "Type": "Task",
      "Resource": "arn:aws:states:::sqs:sendMessage.waitForTaskToken",
      "Parameters": {
        "QueueUrl": "https://sqs.<region>.amazonaws.com/<account>/ir-approval",
        "MessageBody": {
          "instanceId.$": "$.instanceId",
          "incidentId.$": "$.incidentId",
          "taskToken.$": "$$.Task.Token"
        }
      },
      "Next": "RecoverOrClose"
    },
    "RecoverOrClose": {
      "Type": "Choice",
      "Choices": [{
        "Variable": "$.decision",
        "StringEquals": "recover",
        "Next": "RecoverFromBackup"
      }],
      "Default": "CloseIncident"
    },
    "RecoverFromBackup": {
      "Type": "Task",
      "Resource": "arn:aws:lambda:<region>:<account>:function:ir-recover",
      "Next": "CloseIncident"
    },
    "CloseIncident": {
      "Type": "Succeed",
      "Comment": "Incident resolved — full audit trail in execution history"
    }
  }
}
```

### Map state for parallel containment across multiple resources

When a single finding affects multiple resources (e.g., a compromised AMI
across 20 EC2 instances), use `Map` state:

```json
"QuarantineAllInstances": {
  "Type": "Map",
  "ItemsPath": "$.instanceIds",
  "MaxConcurrency": 10,
  "Iterator": {
    "StartAt": "QuarantineOne",
    "States": {
      "QuarantineOne": {
        "Type": "Task",
        "Resource": "arn:aws:states:::ssm:start-automation-execution:waitForTaskToken",
        "Parameters": {
          "DocumentName": "AWS-IsolateEC2Instance",
          "Parameters": { "InstanceId.$": "$" }
        },
        "End": true
      }
    }
  },
  "Next": "NotifyComplete"
}
```

### Wait state vs task token

| Pattern | Use when | Trade-off |
|---|---|---|
| `Wait` state with fixed duration | One-shot timer (e.g., "wait 1h for human, then escalate") | Workflow stays "Running" the whole time; clutters dashboard |
| `Task` with `waitForTaskToken` | Human callback via SQS/CLI | Workflow pauses cleanly; resumes on callback or times out |
| `Task` with Activity worker | Long-running external worker | More code; Activity must be polled |

**Always prefer task-token callback for human approval gates.** It is the
cleanest pattern in Step Functions.

## SSM Automation documents

### AWS-managed documents (preferred when applicable)

| Document | What it does |
|---|---|
| `AWS-IsolateEC2Instance` | Moves EC2 to a quarantine SG in a designated subnet |
| `AWS-DisableIAMUserAccessKey` | Deactivates an IAM user's access key |
| `AWS-RevokeSession` | Forces re-evaluation of active STS sessions (effectively revokes) |
| `AWS-RestartEC2InstanceLaunchedTemplate` | Restarts EC2 from a clean launch template |
| `AWS-CreateManagedLinuxInstance` | Launches a managed forensic analysis instance |
| `AWSSupport-ExecuteEC2Rescue` | Runs EC2 Rescue on a compromised instance |

**Invoke via:**

```bash
aws ssm start-automation-execution \
  --document-name AWS-IsolateEC2Instance \
  --parameters InstanceId=i-0abc12345,SubnetId=subnet-xxx \
  --output json
```

### Custom document example (memory capture)

```yaml
schemaVersion: '0.3'
description: Capture memory from a Linux EC2 instance for forensics
assumeRole: '{{ AutomationAssumeRole }}'
parameters:
  InstanceId:
    type: String
  S3Bucket:
    type: String
mainSteps:
  - name: CaptureMemory
    action: aws:runCommand
    inputs:
      DocumentName: AWS-RunShellScript
      InstanceIds:
        - '{{ InstanceId }}'
      Parameters:
        commands:
          - set -euo pipefail
          - insmod /opt/lime/lime.ko "path=/tmp/mem.lime format=lime"
          - aws s3 cp /tmp/mem.lime s3://{{ S3Bucket }}/forensic/$(date +%s)-mem.lime
          - rm /tmp/mem.lime
    timeoutSeconds: 3600
outputs:
  - CaptureMemory.Output
```

## Systems Manager Incident Manager

Incident Manager coordinates humans during a major incident — chat
channel, on-call page, timeline, post-incident report. Layer it on top
of an automated workflow (EventBridge + Step Functions) for full coverage.

### Create a response plan

```bash
aws ssm-incidents create-response-plan \
  --name prod-ir-plan \
  --display-name "Production IR Response Plan" \
  --incident-template '{
    "title": "Production security incident",
    "impact": 5,
    "summary": "Triggered by GuardDuty severity >= 7",
    "notificationTargets": [{
      "snsTopicArn": "arn:aws:sns:us-east-1:111111111111:ir-incident"
    }]
  }' \
  --engagements arn:aws:ssm-contacts:us-east-1:111111111111:contact/oncall \
  --chat-channel '{"chatbotSns": ["arn:aws:sns:us-east-1:111111111111:slack-chatbot"]}' \
  --actions '[{
    "ssmAutomation": {
      "documentName": "AWS-IsolateEC2Instance",
      "roleArn": "arn:aws:iam::111111111111:role/IR-Automation"
    }
  }]'
```

### Trigger an incident

```bash
# Manual trigger from the console or CLI
aws ssm-incidents start-incident \
  --response-plan-arn arn:aws:ssm-incidents::111111111111:response-plan/prod-ir-plan \
  --title "EC2 malware detected by GuardDuty" \
  --impact 5
```

**Auto-trigger from EventBridge:** wire the EventBridge rule target to an
SSM Automation that calls `start-incident`. Or use Chatbot to forward
GuardDuty to Slack and have a human click "Start incident."

## Safety & kill-switch (MANDATORY)

Every IR automation MUST include:

1. **A kill-switch checked BEFORE any action.** Implementations:
   - **Parameter Store:** Step Functions reads `/ir/kill-switch` value;
     if "disabled", the workflow succeeds without taking action.
   - **Lambda guard:** First Lambda checks the parameter; returns early.
   - **EventBridge rule disable:** `aws events disable-rule --name ir-rule`
     is a global kill-switch.

2. **A test in an isolated account.** Every workflow must be tested
   end-to-end (trigger finding -> workflow runs -> resources contained)
   in a non-prod account before deployment. Use AWS Factory or a dedicated
   `security-test` account.

3. **A manual override.** The workflow must allow a human to:
   - Approve continuation (Step Functions task token callback).
   - Roll back (move instance back to prod SG, re-enable IAM key).
   - Escalate (notify a different channel, page a different on-call).

4. **Scoped IAM roles.** The Lambda/SSM/Step Functions execution role
   must have ONLY the permissions needed for the specific actions
   (e.g., `ec2:ModifyInstanceAttribute` on `arn:aws:ec2:*:*:instance/*`
   — NOT `ec2:*` on `*`).

5. **Idempotency.** The workflow must handle being triggered multiple
   times for the same finding without taking the action multiple times
   (e.g., check if the instance is already in the quarantine SG before
   moving it again).

### Kill-switch Parameter Store pattern

```bash
# Create the kill-switch parameter (default: enabled)
aws ssm put-parameter \
  --name /ir/kill-switch \
  --value "enabled" \
  --type String

# Disable the workflow in one command
aws ssm put-parameter \
  --name /ir/kill-switch \
  --value "disabled" \
  --type String \
  --overwrite

# Workflow checks this FIRST; if "disabled", exits without action.
```

## Audit logging

Every IR action MUST be auditable. Three audit surfaces:

1. **CloudTrail** — every AWS API call (Lambda, SSM, EC2, IAM) is logged
   with caller identity, source IP, request parameters. Verify the
   CloudTrail org trail covers the accounts where IR runs.

2. **Step Functions execution history** — every state transition,
   input/output, error, retry. Retained for 90 days by default (extendable
   via CloudWatch Logs integration). Each execution has a unique ARN —
   reference it in the incident ticket.

3. **SSM Automation execution output** — every step's output, status, and
   duration. Accessible via
   `aws ssm get-automation-execution --automation-execution-id <id>`.

**Audit checklist for every workflow:**

- [ ] CloudTrail covers the account/region where the workflow runs.
- [ ] Step Functions execution history retention >= 90 days.
- [ ] SSM Automation outputs include the finding ID and incident ID.
- [ ] Every containment action includes a tag or annotation with the
      incident ID (`IncidentId=<id>`).
- [ ] Notification messages include the Step Functions execution ARN for
      traceability.
- [ ] Post-incident, an Athena query against CloudTrail can reconstruct
      the full action timeline.

## Output format (per workflow)

```text
FINDING_SOURCE: <guardduty | securityhub | cloudwatch-alarm | eventbridge | health>
RESPONSE_SCOPE: <isolate | snapshot | contain | notify | recover | full-playbook>
VERDICT: AUTOMATED | MANUAL_STEP_REQUIRED
WORKFLOW:
  EventBridge rule: <name>
  Step Functions state machine: <arn>
  SSM Automation documents: <list>
  Incident Manager response plan: <arn>
  Lambda functions: <list>
SAFETY:
  - [PASS] Kill-switch implemented (Parameter Store: /ir/kill-switch)
  - [PASS] Tested in isolated account (security-test, account 555555555555)
  - [PASS] Manual override (Step Functions task token callback)
  - [PASS] IAM roles scoped to specific actions
  - [PASS] Idempotency check (instance already quarantined)
AUDIT:
  - [PASS] CloudTrail org trail covers the account
  - [PASS] Step Functions execution history retention: 90 days
  - [PASS] SSM Automation outputs include incident ID tag
  - [PASS] Notification includes execution ARN
FINDINGS:
  - [INFO] Quarantine SG pre-provisioned in VPC vpc-aaaabbbb
  - [WARN] Incident Manager chat channel requires Slack workspace approval
REMEDIATION:
  1. <step 1>
  2. <step 2>
```

### Worked example — AUTOMATED full-playbook

```text
FINDING_SOURCE: guardduty
RESPONSE_SCOPE: full-playbook
VERDICT: AUTOMATED
WORKFLOW:
  EventBridge rule: ir-guardduty-high-severity
  Step Functions state machine: arn:aws:states:us-east-1:111111111111:stateMachine:ir-full-playbook
  SSM Automation documents: AWS-IsolateEC2Instance, AWS-DisableIAMUserAccessKey
  Lambda functions: ir-parse-finding, ir-snapshot-volumes, ir-notify-slack, ir-recover
  Incident Manager response plan: arn:aws:ssm-incidents::111111111111:response-plan/prod-ir-plan
SAFETY:
  - [PASS] Kill-switch: Parameter Store /ir/kill-switch (checked first in state machine)
  - [PASS] Tested in security-test account 555555555555 on 2026-07-30
  - [PASS] Manual approval gate via SQS task token (no fixed timeout)
  - [PASS] Step Functions execution role scoped to ec2, ssm, sns, sqs, lambda
  - [PASS] Lambda idempotency check on quarantine SG
AUDIT:
  - [PASS] CloudTrail org trail active
  - [PASS] Step Functions execution history retention: 90 days
  - [PASS] All EC2 snapshots tagged IncidentId=<id>
  - [PASS] Slack notification includes Step Functions execution ARN
FINDINGS:
  - [INFO] Quarantine SG sg-aaaabbbb pre-provisioned in VPC vpc-ccccdddd
  - [INFO] Slack webhook URL stored in Parameter Store /ir/slack-webhook
  - [WARN] Memory capture SSM document requires LiME kernel module on target AMIs
REMEDIATION: Deploy via:
  aws cloudformation deploy --stack-name prod-ir-workflow \
    --template-file ir-workflow.yaml \
    --capabilities CAPABILITY_NAMED_IAM CAPABILITY_AUTO_EXPAND \
    --parameter-overrides Environment=prod
```

### Worked example — MANUAL_STEP_REQUIRED (missing kill-switch)

```text
FINDING_SOURCE: guardduty
RESPONSE_SCOPE: full-playbook
VERDICT: MANUAL_STEP_REQUIRED
WORKFLOW: (partial — generated but blocked)
SAFETY:
  - [FAIL] No kill-switch — workflow proceeds unconditionally on every finding
  - [PASS] Tested in security-test account
  - [FAIL] No manual approval gate — runs to completion without human check
  - [WARN] Lambda role has ec2:* on Resource:* (too broad)
AUDIT:
  - [PASS] CloudTrail covers the account
  - [FAIL] SSM Automation outputs do not include incident ID
FINDINGS:
  - [CRITICAL] No kill-switch: a misconfigured GuardDuty detector can trigger
    hundreds of containment actions per minute. A false-positive storm during
    a red-team exercise could quarantine every EC2 instance in the account.
  - [CRITICAL] No manual approval gate: the workflow runs EC2 quarantine +
    IAM key revocation + recovery automatically, with no human checkpoint
    between containment and recovery.
  - [HIGH] Lambda role grants ec2:* on Resource:* — least-privilege violation.
REMEDIATION:
  1. Add a kill-switch: Step Functions Choice state reading Parameter Store /ir/kill-switch
  2. Add a manual approval gate: SQS task-token callback before recovery
  3. Scope the Lambda role to ec2:ModifyInstanceAttribute on specific instance ARNs
  4. Tag SSM Automation outputs with the incident ID via tag-specifications
```

## NEVER (these things)

- NEVER deploy an IR workflow without a kill-switch. The kill-switch is
  the single most important safety mechanism. A workflow that auto-triggers
  on every GuardDuty finding of severity >= 7 without a kill-switch is an
  outage waiting to happen — a false-positive storm during a red-team
  exercise, a misconfigured detector, or a planned penetration test can
  trigger hundreds of containment actions per minute.

- NEVER auto-delete any resource during incident response. Containment
  (reversible) is allowed: move EC2 to quarantine SG, disable IAM key,
  block IP in WAF. Destruction (irreversible) is forbidden: do not
  `delete-user`, `terminate-instance`, `delete-bucket`. Capture state
  (snapshot, CloudTrail export) and escalate to a human for destructive
  actions.

- NEVER grant the IR workflow's IAM role `ec2:*` or `iam:*` on `*`. Scope
  to specific actions: `ec2:ModifyInstanceAttribute` on
  `arn:aws:ec2:*:*:instance/*`, `iam:UpdateAccessKey` on
  `arn:aws:iam::*:user/*`. A workflow that can terminate any EC2 instance
  or delete any IAM user is a privilege-escalation target — if the
  workflow itself is compromised, it becomes the attacker's tool.

- NEVER skip the isolated-account test. A workflow tested only in the
  security-test account, never in prod, may have region-specific IAM
  gaps, missing SSM agent versions, or incorrect EventBridge patterns
  that fail silently on first real incident.

- NEVER use a `Wait` state with a fixed duration for human approval.
  Workflows stuck in `Wait` for 24+ hours clutter the Step Functions
  dashboard, hide real-running executions, and may hit the 1-year
  execution limit silently. Use `Task` with `waitForTaskToken` for human
  callback — it pauses cleanly and resumes on callback.

- NEVER trigger IR automation on AWS Health events alone for resource-
  level threats. Health covers account-level issues (compromised root
  credentials, exposed access keys); it does NOT cover EC2 malware or
  anomalous API calls. Use GuardDuty for resource-level detection.

- NEVER assume SNS notifications will be delivered. SNS requires endpoint
  confirmation for email/HTTPS subscriptions. A topic with an unconfirmed
  subscription silently drops messages. Always send a test message after
  creating the topic, and verify the subscription status before relying
  on the notification.

- NEVER hardcode Slack/Teams webhook URLs in Lambda code or environment
  variables. Store in Parameter Store (free, encrypted by default) or
  Secrets Manager (paid, KMS-encrypted, rotation support). A hardcoded
  URL in a Lambda leaked via CloudTrail `GetFunctionConfiguration` is a
  phishing vector — anyone with the URL can post to your Slack channel.

- NEVER rely on `update-access-key --status Inactive` alone for IAM
  revocation. Active STS sessions continue until they expire (up to 12
  hours). To kill active sessions, also call `put-user-policy` with an
  explicit Deny on `*:*`, or use the SSM managed document
  `AWS-RevokeSession`.

- NEVER snapshot AFTER isolating an EC2 instance if memory forensics is
  required. Memory changes during the isolation process. Order: capture
  memory first (RAM), snapshot EBS second (disk), isolate third
  (network). Reversing the order loses evidence.

- NEVER trigger IR automation on GuardDuty findings without filtering on
  `service.serviceName`. Multi-account aggregations have multiple
  detectors; an unfiltered rule triggers on findings from any detector,
  including detectors in test accounts.

- NEVER assume `AWS-IsolateEC2Instance` works without the quarantine SG
  pre-provisioned. The document moves the instance to a designated
  subnet — if the subnet does not exist or the SG does not exist, the
  document fails silently. Pre-provision in every VPC where IR runs.

- NEVER use CloudTrail as the detection source for near-real-time
  containment. CloudTrail event delivery latency is 3-15 minutes via
  EventBridge. For sub-minute detection, use GuardDuty directly (its
  own delivery path) or CloudWatch Metrics/alarms.

- NEVER forget to test the kill-switch itself. A kill-switch that fails
  to disable the workflow is worse than no kill-switch — it gives false
  confidence. Test by setting the parameter to "disabled" and triggering
  the workflow; verify no action is taken.

- NEVER let the IR workflow run with no execution retention. Step
  Functions defaults to 90-day history; if the incident investigation
  runs longer (forensics, legal), configure CloudWatch Logs integration
  to extend retention to 1 year+.

- NEVER assume cross-account containment works without pre-deployed
  roles. The security account's Lambda cannot directly call
  `ec2:ModifyInstanceAttribute` in a member account. Deploy
  `IncidentResponseRole` in every member account with a trust policy
  allowing the security account's role to assume it. Test the assume-
  role path before relying on it for incident response.

- NEVER use `aws ssm create-association` for one-shot containment. SSM
  associations are scheduled (rate-based or cron), not immediate. Use
  `aws ssm start-automation-execution` for one-shot containment actions.

## Pre-flight safety checks (run before any deploy)

- **MANDATORY CONFIRMATION GATE.** Before any state-changing operation
  (`cloudformation deploy`, `stepfunctions update-state-machine`,
  `events put-rule`, `ssm create-document`), the automator MUST emit:
  `CONFIRM: About to <action> for <workflow> in account <account>. This
  affects <consequence>. Proceed? (yes/no)` and wait for explicit `yes`.

- **Dry-run the EventBridge rule.** Before enabling the rule that
  triggers the workflow, run with the rule in `DISABLED` state, send a
  test event via `aws events put-events`, and verify the Step Functions
  execution starts. Then enable the rule for production findings.

- **Validate the kill-switch first.** Before wiring the EventBridge rule
  to a real detector, set `/ir/kill-switch` to "disabled" and verify a
  test finding does NOT trigger containment. Then flip to "enabled" and
  verify it does.

- **Capture the existing state.** Before deploying a workflow that
  modifies resources, snapshot the existing state:
  `aws ec2 describe-security-groups --group-ids <quarantine-sg>` and
  `aws guardduty list-detectors` to a backup file. If the workflow
  misbehaves, you have a rollback baseline.

- **Verify Slack/Teams webhook.** Send a test message to the configured
  webhook URL before relying on it for incident notifications. A
  misconfigured webhook URL silently drops messages.

- **Test in security-test account FIRST.** Run the full workflow end-to-
  end (trigger finding -> workflow runs -> resources contained) in a
  dedicated test account. Use AWS Factory or a non-prod account. Do not
  deploy to prod without a passing test run.

- **Verify incident ID propagation.** Every action, snapshot, SSM
  execution, and notification must include the incident ID. Verify by
  inspecting the Step Functions execution output and the S3 forensic
  bucket tags after a test run.

## Edge-case handling

- **Finding for a missing resource.** GuardDuty may emit a finding for an
  EC2 instance that was terminated between detection and containment. The
  Lambda must handle `InvalidInstanceID.NotFound` gracefully — log it and
  move on. Do not retry the failed action; the resource is gone.

- **Workflow triggered during deployment.** A deployment that updates the
  IR workflow may trigger it on a stale EventBridge event. Use versioned
  state machine ARNs (`stateMachine:ir-full-playbook:3`) and only point
  EventBridge at the latest version after deployment completes.

- **Cross-region incident.** A compromise in us-east-1 may affect
  resources in eu-west-1. The EventBridge rule must either be deployed
  in every region, or use EventBridge global endpoint bus to forward
  findings to a central region for processing.

- **Red-team exercise.** During a planned red-team exercise, the IR
  workflow will fire on red-team activity. The kill-switch exists for
  this scenario — disable it before the exercise, re-enable after.
  Communicate the disable window to the on-call.

- **Quarantine SG deletion.** If someone deletes the quarantine SG
  (intentionally or accidentally), `AWS-IsolateEC2Instance` fails. Set
  `DeletionProtection` (via CloudFormation `DeletionPolicy: Retain`) on
  the quarantine SG. Monitor for deletion attempts via Config rule.

- **Slack/Teams webhook rotation.** Webhook URLs expire or are rotated.
  Store in Parameter Store with a `LastRotated` tag; alert if >90 days.

- **Multi-account aggregate finding.** A finding from a member account
  arrives at the management account's GuardDuty aggregator. The
  `accountId` field in the finding identifies the source. The workflow
  must use that `accountId` to assume the member's `IncidentResponseRole`
  before containment.

## Reference — IR orchestration comparison

| Dimension | Lambda-only | Step Functions | SSM Automation | Incident Manager |
|---|---|---|---|---|
| Use case | Single-action, fast | Multi-phase, parallel, approval | AWS-curated playbook | Human coordination |
| Max duration | 15 min | 1 year | 1 hour/step (default) | Incident lifetime |
| State | Stateless | Stateful (execution) | Stateless (one-shot) | Stateful (incident record) |
| Error handling | Lambda retries | Step Functions retries/catch | Document-level | Manual |
| Approval gate | Via SQS | Native (task token) | No | Manual |
| Audit | CloudTrail | Execution history + CloudTrail | Execution output + CloudTrail | Incident timeline |
| Cost model | Per-invocation | Per-state-transition | Per-execution | Per-incident |

## Recent AWS features (2024-2026)

- **GuardDuty Runtime Monitoring for ECS/EKS (2024-2025):** Detects
  container-level threats (malicious process execution, reverse shell,
  cryptocurrency mining inside a container). Findings include
  `ContainerDetails` block. Containment pattern: stop the ECS task or
  evict the EKS pod, NOT quarantine SG (pods do not have SGs directly).
- **Security Hub custom actions (2024-2025):** Custom actions can now be
  triggered from the Security Hub console or API, forwarding findings to
  EventBridge for analyst-initiated containment. Useful for "right-click
  and isolate this EC2" workflows.
- **Incident Manager chat (2024-2025):** AWS Chatbot integration with
  Incident Manager auto-creates a Slack/Chime channel per incident,
  inviting the on-call. Hand-offs and timeline updates post to the
  channel automatically. Configure via
  `aws chatbot create-slack-channel-configuration`.
- **Step Functions Distributed Map (2024-2025):** Map state can now
  iterate over large datasets (S3 listing, DynamoDB scan) for parallel
  processing. Use for "isolate every EC2 instance matching this tag"
  workflows.
- **SSM Automation AWS-ValidateQuarantineSG (2024):** New managed
  document that pre-validates the quarantine SG configuration before
  `AWS-IsolateEC2Instance` runs. Catches the "SG was deleted" failure
  mode before the actual isolation.
- **EventBridge global endpoints (2024-2025):** Multi-region event bus
  failover. Use for cross-region IR — a primary event bus in us-east-1
  with a failover to us-west-2 ensures IR triggers continue during a
  regional event.
- **GuardDuty Malware Protection for S3 (2024-2025):** Scans S3 objects
  for malware on upload. Findings have `Service.AdditionalInfo.MalwareScan`.
  Use for IR workflows that quarantine S3 objects (move to isolated
  bucket, deny public access).
- **Security Hub Automated Security Response on AWS (ASR) (2024-2025):**
  AWS-published solution with pre-built EventBridge-to-SSM-remediation
  playbooks for common Security Hub findings. Deploy as a starting point
  for org-wide IR automation; customize per-resource.

## Domain

AWS CloudOps / Security Incident Response Automation.

## AWS documentation

- **AWS GuardDuty User Guide** — https://docs.aws.amazon.com/guardduty/latest/ug/
- **AWS Security Hub User Guide** — https://docs.aws.amazon.com/securityhub/latest/userguide/
- **AWS Step Functions Developer Guide** — https://docs.aws.amazon.com/step-functions/latest/dg/
- **AWS Systems Manager Automation** — https://docs.aws.amazon.com/systems-manager/latest/userguide/systems-manager-automation.html
- **AWS Systems Manager Incident Manager** — https://docs.aws.amazon.com/incident-manager/latest/userguide/
- **AWS EventBridge User Guide** — https://docs.aws.amazon.com/eventbridge/latest/userguide/
- **AWS Incident Response Guide** — https://docs.aws.amazon.com/whitepapers/latest/aws-incident-response/
- **AWS Security Incident Response Blog** — https://aws.amazon.com/blogs/security/
- **Automated Security Response on AWS** — https://aws.amazon.com/solutions/implementations/automated-security-response-on-aws/
