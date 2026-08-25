---
name: incident-response-automator
description: 'Designs automated AWS incident response workflows across detection (GuardDuty, Security Hub, CloudWatch alarms, EventBridge, AWS Health) and response patterns (EC2 quarantine SG, IAM credential revocation, EBS forensic snapshot, memory capture via SSM, WAF/NACL IP block, secret rotation, session revoke), notification (SNS/Slack/Teams via Lambda, on-call paging), and recovery (restore from backup, clean AMI redeploy). Orchestrates via EventBridge rule (GuardDuty severity >= 7) to Step Functions state machine (isolate, snapshot, notify, human approval, recover), SSM Automation documents (AWS-IsolateEC2Instance, AWS-DisableIAMUserAccessKey, AWS-RevokeSession), and Systems Manager Incident Manager. Enforces safety: kill-switch required, isolated-account testing, manual override, full CloudTrail + Step Functions audit. Emits verdict AUTOMATED with response plan or MANUAL_STEP_REQUIRED with gap. Use when designing IR playbooks or wiring GuardDuty/Security Hub to remediation.'
license: Apache-2.0
compatibility: Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). No AWS CLI required for offline plan authoring. Live deployment uses aws guardduty list-detectors/create-filter, aws events put-rule, aws stepfunctions create-state-machine, aws ssm create-document, aws ssm-incidents create-response-plan, aws iam update-access-key / delete-role-policy, aws ec2 modify-instance-attribute, aws ssm start-automation-execution. Requires AWS CLI v2 with guardduty, ssm, ssm-incidents...
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: 'true'
  phase: '4'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: Security
  task_type: automate
  skill_class: capability
  lifecycle_status: active
  verdict_shape: AUTOMATED | MANUAL_STEP_REQUIRED
  when_to_use: Designing an automated incident response workflow for AWS, wiring GuardDuty or Security Hub findings to automated containment actions, building a Step Functions state machine that orchestrates isolate- snapshot-notify-recover, creating SSM Automation documents for containment (quarantine SG, IAM key revoke, session revoke), standing up an Incident Manager response plan with chat channel and on-call engagement, or hardening an existing IR automation with kill-switch and manual override.
  when_not_to_use: Manual incident triage — this skill designs automation; use a triage skill for human-driven investigation., AWS Config rule remediation (different mechanism — uses SSM Automation but triggered by Config non-compliance, not a finding)., Disaster recovery (DR) orchestration — DR is about service continuity, not threat containment; use a DR/backup-restore skill., Patch management at scale — use SSM Patch Manager, not IR automation.
  activation_triggers: automate incident response, GuardDuty to Lambda remediation, Step Functions for incident response, EC2 quarantine security group, revoke IAM access key automatically, forensic EBS snapshot, SSM Automation document for containment, Incident Manager response plan, EventBridge rule for GuardDuty finding, kill-switch for IR automation, automated WAF block on attacker IP
  invocation_schema: "{output: \"Deterministic block: FINDING_SOURCE / RESPONSE_SCOPE / VERDICT / WORKFLOW\\\n    \\ / SAFETY / AUDIT / FINDINGS / REMEDIATION. VERDICT is one of AUTOMATED | MANUAL_STEP_REQUIRED.\\\n    \\ AUTOMATED means the workflow is complete, includes a kill-switch, has been validated\\\n    \\ in an isolated test account, and covers audit logging. MANUAL_STEP_REQUIRED\\\n    \\ means one or more safety/coverage gates failed \\u2014 the output enumerates\\\n    \\ the specific gap and the required manual fix.\", properties: {existing_workflow: {\n      description: 'An existing EventBridge rule + Step Functions state machine definition\n        (Amazon States Language JSON). When provided, the skill runs the safety +\n        audit gate and emits AUTOMATED or MANUAL_STEP_REQUIRED.', type: object}, finding_source: {\n      description: The detection source that triggers the workflow., enum: [guardduty,\n        securityhub, cloudwatch-alarm, eventbridge, health], type: enum}, response_scope: {\n      description: Which response phases to automate., enum: [isolate, snapshot, contain,\n        notify, recover, full-playbook], type: enum}, severity_threshold: {description: 'Minimum\n        finding severity (GuardDuty scale 0-10, Security Hub normalized to 0-100).\n        Default 7.0 (GuardDuty) / 70 (SH).', type: number}}, required: [finding_source,\n    response_scope], type: object}"
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  keywords: incident response, GuardDuty, Security Hub, CloudWatch alarm, EventBridge, AWS Health, Step Functions, SSM Automation, Systems Manager, Incident Manager, response plan, EC2 quarantine, IAM credential revocation, EBS snapshot, forensic preservation, WAF block, secret rotation, revoke session, SNS notification, Lambda, kill-switch, automated remediation
  tags: security, incident-response, automation, guardduty, securityhub, ssm, stepfunctions, eventbridge, incident-manager
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

→ Extended Mindset rationale moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).

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

→ Live-account pre-flight command listing moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md).

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

→ Orchestration-surface selection notes moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).

## Step 0: Expert knowledge — non-obvious IR behaviors

→ Step-0 expert-knowledge deep dive moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).

## Detection sources

### GuardDuty (preferred for resource-level threats)

→ GuardDuty detector/filter CLI commands moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md).

→ GuardDuty EventBridge event pattern moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).

**Finding types worth automating on:**
- `UnauthorizedAccess:EC2/SSHBruteForce` — auto-block source IP in WAF/NACL.
- `UnauthorizedAccess:EC2/RDPBruteForce` — auto-block source IP.
- `Impact:EC2/PortSweep` — quarantine the EC2 instance (it is compromised).
- `CredentialAccess:IAMUser/AnomalousBehavior` — revoke IAM credentials.
- `Trojan:EC2/SSHBruteForce` or `Trojan:EC2/DGADomainRequest` — isolate.
- `Persistence:IAMUser/BackdoorUser` — revoke + investigate.

### Security Hub (preferred for aggregated multi-detector findings)

→ Security Hub EventBridge event pattern moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).

**Custom actions:** Security Hub supports custom actions triggered from
the console or API. Wire a custom action to an EventBridge rule for
analyst-initiated containment (no auto-trigger).

### CloudWatch alarms

→ CloudWatch alarm EventBridge event pattern moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).

Use for threshold-based detection: anomalous API call volume, unusual
egress traffic, spike in failed logins.

### EventBridge custom events

For application-level signals that do not map to a GuardDuty or Security
Hub finding type: a custom event from a Lambda or ECS task indicating
"detected malicious input" or "container exited with security signal."

### AWS Health events

→ AWS Health EventBridge event pattern moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).

Use for AWS-detected account-level incidents (exposed access keys,
compromised root credentials).

## Response patterns

### 1. Isolate compromised resource

→ Response-pattern 1 implementation commands moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md).

### 2. Forensic preservation

→ Response-pattern 2 implementation commands moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md).

### 3. Containment (block attacker)

→ Response-pattern 3 implementation commands moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md).

### 4. Notification

→ Response-pattern 4 implementation commands moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md).

### 5. Recovery

→ Response-pattern 5 implementation commands moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md).

## Step Functions orchestration

For full-playbook IR (multi-phase, parallel, human-approval), use Step
Functions. The state machine below orchestrates the canonical pattern:

→ Full-playbook ASL state machine moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).

### Map state for parallel containment across multiple resources

When a single finding affects multiple resources (e.g., a compromised AMI
across 20 EC2 instances), use `Map` state:

→ Map-state parallel containment pattern moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).

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

→ AWS-managed document invoke commands moved verbatim to [references/ssm-automation-catalog.md](references/ssm-automation-catalog.md).

### Custom document example (memory capture)

→ Custom memory-capture SSM document moved verbatim to [references/ssm-automation-catalog.md](references/ssm-automation-catalog.md).

## Systems Manager Incident Manager

Incident Manager coordinates humans during a major incident — chat
channel, on-call page, timeline, post-incident report. Layer it on top
of an automated workflow (EventBridge + Step Functions) for full coverage.

→ Incident Manager response-plan + trigger CLI moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md).

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

→ Kill-switch Parameter Store CLI pattern moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md).

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

→ Audit checklist moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md).

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

→ Secondary worked example moved verbatim to [references/worked-examples.md](references/worked-examples.md).

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

→ Pre-flight safety checks moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md).

## Edge-case handling

→ Edge-case catalog moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).

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

→ Recent AWS features catalog moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).

## References (load on demand)

- [references/worked-examples.md](references/worked-examples.md) — secondary worked example: MANUAL_STEP_REQUIRED verdict (missing kill-switch).
- [references/diagnostic-commands.md](references/diagnostic-commands.md) — live-account pre-flight checks; response-pattern implementation commands (isolate / snapshot / contain / notify / recover); Incident Manager and kill-switch CLI; pre-flight safety checks; audit checklist.
- [references/advanced-patterns.md](references/advanced-patterns.md) — extended Mindset rationale; Step-0 expert knowledge; orchestration-surface notes; detection-source EventBridge patterns; full-playbook ASL state machine and Map state; edge cases; recent AWS features.
- [references/ssm-automation-catalog.md](references/ssm-automation-catalog.md) — extended: AWS-managed document invoke commands and the custom memory-capture document.

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
