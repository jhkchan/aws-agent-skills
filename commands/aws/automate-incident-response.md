---
description: Design and implement automated AWS incident response workflows. Wire GuardDuty/Security Hub findings to Step Functions orchestration (isolate, snapshot, notify, recover), SSM Automation documents, and Systems Manager Incident Manager. Enforces kill-switch, isolated-account testing, manual override, full CloudTrail audit.
nl_triggers:
  - "automate incident response"
  - "GuardDuty to Lambda remediation"
  - "Step Functions for incident response"
  - "EC2 quarantine security group"
  - "revoke IAM access key automatically"
  - "forensic EBS snapshot"
  - "SSM Automation document for containment"
  - "Incident Manager response plan"
  - "EventBridge rule for GuardDuty finding"
  - "kill-switch for IR automation"
  - "automated WAF block on attacker IP"
  - "memory capture for forensics"
  - "revoke active STS sessions"
routes_to: incident-response-automator
---

# /aws:automate-incident-response

Activate the `incident-response-automator` skill and produce an incident
response workflow design (or validation report).

## What it does

Reads a finding source (GuardDuty, Security Hub, CloudWatch alarm,
EventBridge, AWS Health), a response scope (isolate, snapshot, contain,
notify, recover, or full-playbook), and either:

1. **Designs** a complete workflow with: EventBridge rule pattern, Step
   Functions state machine (ASL JSON), SSM Automation document
   invocations, Lambda functions for snapshot/notify/recover, IAM roles
   scoped to specific actions, kill-switch, manual approval gate.
2. **Validates** an existing workflow against the mandatory safety
   baseline (kill-switch required, isolated-account test, scoped IAM,
   idempotency, audit logging, no auto-destructive actions).

Emits a deterministic block per workflow:

```text
FINDING_SOURCE: <guardduty | securityhub | cloudwatch-alarm | eventbridge | health>
RESPONSE_SCOPE: <isolate | snapshot | contain | notify | recover | full-playbook>
VERDICT: AUTOMATED | MANUAL_STEP_REQUIRED
WORKFLOW:
  EventBridge rule: <name>
  Step Functions state machine: <arn>
  SSM Automation documents: <list>
  Lambda functions: <list>
  Incident Manager response plan: <arn or none>
SAFETY:
  - [PASS|FAIL] Kill-switch implemented
  - [PASS|FAIL] Tested in isolated account
  - [PASS|FAIL] Manual approval gate
  - [PASS|FAIL] IAM roles scoped to specific actions
  - [PASS|FAIL] Idempotency check
  - [PASS|FAIL] No destructive actions
AUDIT:
  - [PASS|FAIL] CloudTrail covers the account
  - [PASS|FAIL] Step Functions execution history retention >= 90 days
  - [PASS|FAIL] SSM outputs tagged with IncidentId
  - [PASS|FAIL] Notifications include execution ARN
FINDINGS:
  - [INFO|WARN|HIGH|CRITICAL] <observation>
REMEDIATION:
  <numbered steps for fixing any FAIL findings>
```

## When to invoke

Provide a finding source + response scope and ask any of:

- "automate EC2 quarantine on GuardDuty severity >= 7"
- "build a Step Functions incident response playbook"
- "revoke IAM access keys on CredentialAccess findings"
- "create an Incident Manager response plan for production"
- "validate our existing IR workflow for safety gaps"
- "add a kill-switch to our GuardDuty auto-remediation"

A bare finding source + response scope + "automate" routes here via the
orchestrator.

## Inputs

- **Required:** finding_source (guardduty | securityhub |
  cloudwatch-alarm | eventbridge | health), response_scope (isolate |
  snapshot | contain | notify | recover | full-playbook).
- **Recommended:** severity_threshold (default 7.0 for GuardDuty, 70 for
  Security Hub), test_account_id (for the isolated-account test gate),
  kill_switch_type (parameter-store | lambda-choice | eventbridge-disable).
- **For validation mode:** existing_workflow (EventBridge rule JSON +
  Step Functions ASL + IAM role policy JSON).

## Outputs

- One VERDICT block per workflow (AUTOMATED or MANUAL_STEP_REQUIRED).
- The complete workflow design (EventBridge rule, Step Functions ASL,
  SSM documents, Lambda stubs, IAM role policies) in WORKFLOW.
- Safety gate pass/fail per dimension in SAFETY.
- Audit gate pass/fail per dimension in AUDIT.
- Specific remediation steps for any failing gate in REMEDIATION.

## Related

- `/aws:pipeline` to enter the full CloudOps pipeline (this skill is the
  Phase 4 Automate specialist for incident response).
- `/aws:triage-guardduty-findings` for human-driven GuardDuty finding
  triage (this skill designs automation; triage is interactive).
- `/aws:audit-securityhub-control-compliance` for Security Hub control
  posture (a detection source for this skill's workflows).
- `/aws:automate-iac-template` to generate the CloudFormation template
  that deploys the IR workflow resources.
