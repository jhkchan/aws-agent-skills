---
description: Design AWS Config + SSM Automation remediation workflows with safety gates, audit, and the correct automatic-vs-manual trigger.
nl_triggers:
  - "automate Config remediation"
  - "wire SSM to Config rule"
  - "put-remediation-configurations"
  - "automatic remediation setup"
  - "conformance pack remediation"
  - "EventBridge Lambda remediation"
  - "SSM Automation runbook for Config"
  - "NON_COMPLIANT auto-fix"
  - "remediation safety gate"
  - "Config timeline verification"
  - "SSM Change Manager workflow"
  - "AWS-DisableS3BucketPublicAccess"
  - "AWS-IAMRevokeUnusedAccessKey"
  - "remediation configuration"
routes_to: auto-remediation-automator
---

# /aws:automate-remediation-workflow

Activate the `auto-remediation-automator` skill and design a remediation
workflow linking AWS Config rules to SSM Automation runbooks with the
correct trigger semantics and safety gates.

## What it does

Reads a Config rule definition plus target NON_COMPLIANT resource
examples, then applies a 10-step design process:

1. Classify the trigger source (managed / periodic / custom / org pack).
2. Map the resource type to a remediation strategy.
3. Pick or design the SSM Automation document.
4. Decide automatic vs manual trigger (the trigger matrix).
5. Wire `put-remediation-configurations` with the right parameter mapping.
6. Build a custom SSM Automation document if no managed runbook fits.
7. Use EventBridge + Lambda as an alternative when SSM is too constrained.
8. Roll out bulk remediation via conformance packs.
9. Add safety gates (snapshot, dry-run, approval, Change Manager).
10. Audit and verify end-to-end (SSM execution status + Config timeline).

Emits a deterministic VERDICT per rule:

```text
REMEDIATION: <reference>
RULE: <rule-name>
RESOURCE_TYPE: <AWS::...>
WORKFLOW: <detection/runbook/trigger/safety/audit>
TRIGGER: AUTOMATIC | MANUAL
SAFETY: <gates applied>
AUDIT: <CloudTrail + Config verification steps>
VERDICT: AUTOMATED | MANUAL_STEP_REQUIRED
GAP: <if MANUAL_STEP_REQUIRED, the specific missing piece>
TEMPLATE: <CLI snippet or YAML for the remediation configuration>
```

## When to invoke

Paste a Config rule definition and target resource examples and ask:

- "design auto-remediation for this Config rule"
- "wire SSM Automation to my Config findings"
- "should this remediation be automatic or manual?"
- "build a conformance pack with remediation"
- "hardening my remediation workflow with safety gates"
- "verify a remediation that already executed"

A bare Config rule name + any automate verb ("automate S3 public
access remediation", "wire IAM key revocation") also routes here via
the orchestrator.

## Inputs

- Config rule definition (managed identifier or custom Lambda rule)
  with scope and source.
- Sample NON_COMPLIANT resource IDs for the rule.
- SSM service role ARN (defaults to
  `arn:aws:iam::<account>:role/aws-service-role/AmazonSSMAutomationRole/AWS-SSM-AutomationExecutionRole`).
- Pre-prod validation status (whether the runbook has been tested on
  real NON_COMPLIANT resources).
- For destructive remediations: application-impact context (which
  workloads depend on the resource).

## Outputs

- One REMEDIATION block per rule with WORKFLOW, TRIGGER, SAFETY,
  AUDIT, VERDICT, and TEMPLATE fields.
- For AUTOMATED verdicts: a working `put-remediation-configurations`
  CLI call with the exact parameter mapping.
- For MANUAL_STEP_REQUIRED verdicts: a specific GAP citation (missing
  custom runbook, destructive change requiring Change Manager, missing
  pre-prod validation, etc.).
- Safety-gate recommendations for every workflow.

## Related

- `/aws:pipeline` to enter the full CloudOps pipeline (this skill is
  the Phase 4 Automate specialist for Config-driven governance).
- `/aws:audit-config-recorder-coverage` to verify the Config recorder
  is capturing the resource types the remediation targets.
- `/aws:audit-iam-least-privilege` for IAM-policy-detach remediations
  that require least-privilege analysis before wiring.
