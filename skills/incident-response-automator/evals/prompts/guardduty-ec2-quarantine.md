# Eval prompt: guardduty-ec2-quarantine

Design an automated incident response workflow. Emit the standard VERDICT
block (FINDING_SOURCE, RESPONSE_SCOPE, VERDICT, WORKFLOW, SAFETY, AUDIT,
FINDINGS, REMEDIATION).

Finding source: guardduty
Response scope: isolate (EC2 only)
Severity threshold: 7.0

Requirements:
- EventBridge rule pattern: source=aws.guardduty, detail-type=GuardDuty
  Finding, detail.severity >= 7, detail.service.serviceName=guardduty
- Containment action: invoke SSM Automation document
  AWS-IsolateEC2Instance with InstanceId and SubnetId (quarantine subnet
  pre-provisioned in every VPC where IR runs)
- Kill-switch: Step Functions reads /ir/kill-switch from Parameter Store
  as the first state; if "disabled", the workflow succeeds without action
- Manual override: Step Functions task-token callback via SQS for approval
  before recovery (if any)
- Notification: SNS topic -> Lambda subscription -> Slack incoming webhook
  (URL stored in Parameter Store /ir/slack-webhook)
- IAM role for Lambda: scoped to ec2:ModifyInstanceAttribute on
  arn:aws:ec2:*:*:instance/*, ssm:StartAutomationExecution on
  AWS-IsolateEC2Instance, sns:Publish on the IR topic
- Idempotency: Lambda checks the instance's current SGs before swapping;
  if already in quarantine SG, no-op
- Tested in isolated account: security-test (555555555555) on 2026-07-30

Expected: AUTOMATED. The workflow includes all mandatory safety gates
(kill-switch, isolated test, manual override, scoped IAM, idempotency)
and full audit logging (CloudTrail, Step Functions execution history).
