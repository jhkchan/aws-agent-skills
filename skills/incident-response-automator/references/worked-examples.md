# Incident Response Automator — worked examples (moved verbatim from SKILL.md)

> Progressive-disclosure split: this content was moved verbatim from SKILL.md; nothing was rewritten.

## Worked example — MANUAL_STEP_REQUIRED (missing kill-switch)

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
