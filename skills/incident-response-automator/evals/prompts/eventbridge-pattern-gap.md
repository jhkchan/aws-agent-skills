# Eval prompt: eventbridge-pattern-gap

Validate this existing EventBridge rule for an IR workflow. Emit the
standard VERDICT block (FINDING_SOURCE, RESPONSE_SCOPE, VERDICT, WORKFLOW,
SAFETY, AUDIT, FINDINGS, REMEDIATION).

Existing rule pattern:
```json
{
  "source": ["aws.guardduty"],
  "detail-type": ["GuardDuty Finding"]
}
```

Target: Step Functions state machine ir-full-playbook

Other workflow characteristics:
- Kill-switch: present (Parameter Store /ir/kill-switch checked first in
  the state machine)
- Manual approval gate: present (SQS task-token callback)
- IAM role for Step Functions: scoped correctly to specific actions on
  specific resources
- Idempotency: present (Lambda checks current SG before action)
- Audit: CloudTrail + Step Functions execution history retention 90 days
- Tested in security-test account

Expected: MANUAL_STEP_REQUIRED. The skill must detect that the EventBridge
rule pattern is missing the severity filter and the service-name filter.
Without these:
- The workflow triggers on EVERY GuardDuty finding (severity 0-10),
  including informational findings like "New.Malware" or service events.
- The workflow triggers on findings from ALL detectors in the account
  (including test detectors in non-prod VPCs).

The skill must recommend adding:
- detail.severity: [{"numeric": [">=", 7]}]
- detail.service.serviceName: ["guardduty"]
