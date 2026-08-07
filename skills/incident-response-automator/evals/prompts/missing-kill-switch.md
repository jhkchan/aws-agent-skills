# Eval prompt: missing-kill-switch

Validate this existing incident response workflow. Emit the standard
VERDICT block (FINDING_SOURCE, RESPONSE_SCOPE, VERDICT, WORKFLOW, SAFETY,
AUDIT, FINDINGS, REMEDIATION).

Existing workflow:

EventBridge rule pattern:
```json
{
  "source": ["aws.guardduty"],
  "detail-type": ["GuardDuty Finding"],
  "detail": {
    "severity": [{"numeric": [">=", 7]}]
  }
}
```
Target: Lambda function ir-quarantine

Lambda execution role policy:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": "ec2:*",
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": ["iam:UpdateAccessKey", "iam:PutUserPolicy"],
      "Resource": "*"
    }
  ]
}
```

Workflow logic (in Lambda):
1. Receive finding event
2. Extract instanceId from finding detail
3. Call ec2:ModifyInstanceAttribute to swap SGs to quarantine
4. For each volume, call ec2:CreateSnapshot
5. Call sns:Publish to notify
6. Call ec2:TerminateInstances on the instance

Characteristics:
- No kill-switch (Lambda does not check any parameter before action)
- No human approval gate (steps 1-6 run without pause)
- No isolated-account test
- No idempotency check (Lambda does not verify current SG before swap)
- SSM Automation outputs not tagged with incident ID

Expected: MANUAL_STEP_REQUIRED. The skill must flag multiple CRITICAL
safety gaps:
1. No kill-switch — fails the mandatory safety baseline.
2. ec2:TerminateInstances is auto-destruction — violates "containment is
   reversible, destruction is not."
3. ec2:* on Resource:* and iam:UpdateAccessKey on Resource:* are
   over-broad IAM — least-privilege violation.
4. No human approval gate between containment and destruction.
5. No isolated-account test.
6. No idempotency check.
