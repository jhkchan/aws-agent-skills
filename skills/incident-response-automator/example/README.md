# Example usage: incident-response-automator

A walkthrough showing the skill designing a full-playbook Step Functions
incident response workflow for GuardDuty EC2 findings, with kill-switch,
parallel containment, human approval gate, and full audit logging. The
skill emits an AUTOMATED verdict.

## Input (user prompt)

> Design an automated incident response workflow for our production AWS
> account. When GuardDuty detects a high-severity finding on an EC2
> instance (severity >= 7), I want to: isolate the instance, snapshot
> the volumes, notify the on-call via Slack, wait for human approval,
> then either recover or close. Include a kill-switch and full audit.

## Skill output

```text
FINDING_SOURCE: guardduty
RESPONSE_SCOPE: full-playbook
VERDICT: AUTOMATED
WORKFLOW:
  EventBridge rule: ir-guardduty-ec2-high-severity
  Step Functions state machine: arn:aws:states:us-east-1:111111111111:stateMachine:ir-ec2-full-playbook
  SSM Automation documents: AWS-IsolateEC2Instance
  Lambda functions: ir-parse-finding, ir-snapshot-volumes, ir-notify-slack, ir-recover
  SNS topic: arn:aws:sns:us-east-1:111111111111:ir-ec2-notifications
  SQS queue: https://sqs.us-east-1.amazonaws.com/111111111111/ir-ec2-approval
  Quarantine SG: sg-aaaabbbbcccc (pre-provisioned in vpc-ccccdddd)
  Kill-switch: Parameter Store /ir/ec2-kill-switch (checked first in state machine)
SAFETY:
  - [PASS] Kill-switch: Step Functions reads /ir/ec2-kill-switch; if "disabled", exits
  - [PASS] Tested in isolated account security-test (555555555555) on 2026-07-30
  - [PASS] Manual approval gate via SQS task-token callback (no fixed Wait duration)
  - [PASS] Step Functions execution role scoped to ec2:ModifyInstanceAttribute on
          arn:aws:ec2:*:*:instance/*, ssm:StartAutomationExecution on
          arn:aws:ssm:*:*:automation-definition/AWS-IsolateEC2Instance:*,
          sns:Publish on the IR topic, sqs:SendMessage on the approval queue
  - [PASS] Lambda idempotency: ir-snapshot-volumes checks for existing IncidentId
          tag before snapshotting; ir-parse-finding checks if instance is already
          in quarantine SG before invoking isolation
  - [PASS] No destructive actions: workflow isolates (reversible) but does NOT
          terminate instances or delete IAM users
AUDIT:
  - [PASS] CloudTrail org trail covers account 111111111111
  - [PASS] Step Functions execution history retention: 90 days
  - [PASS] EBS snapshots tagged with IncidentId=<incident-uuid>, Preserve=true
  - [PASS] Slack notification includes Step Functions execution ARN + finding ID
FINDINGS:
  - [INFO] Quarantine SG pre-provisioned in VPC vpc-ccccdddd (DeletionPolicy: Retain)
  - [INFO] Slack webhook URL stored in Parameter Store /ir/slack-webhook (encrypted)
  - [WARN] Memory capture step not included — add if fileless malware is a concern
  - [WARN] Cross-account containment requires IncidentResponseRole in each member
          account — verify deployment before relying on multi-account scenarios
REMEDIATION:
  1. Deploy the CloudFormation stack:
     aws cloudformation deploy --stack-name prod-ir-ec2-workflow \
       --template-file ir-workflow.yaml \
       --capabilities CAPABILITY_NAMED_IAM CAPABILITY_AUTO_EXPAND \
       --parameter-overrides Environment=prod QuarantineSubnetId=subnet-xxx
  2. Confirm the kill-switch is enabled:
     aws ssm put-parameter --name /ir/ec2-kill-switch --value "enabled" --type String
  3. Send a test event to verify the EventBridge rule triggers the state machine:
     aws events put-events --entries file://test-event.json
  4. Verify the Slack webhook delivers by triggering a test execution.
```

## What the skill caught that a generic assistant misses

1. **Kill-switch checked FIRST in the state machine.** A generic
   assistant buries the kill-switch check inside a Lambda — if the
   Lambda fails on the check, the workflow proceeds. The skill puts the
   check as a Step Functions `Task` + `Choice` state, evaluated before
   any action.

2. **update-access-key alone does NOT revoke sessions.** When IAM
   revocation is needed, the skill pairs
   `iam:UpdateAccessKey --status Inactive` with
   `iam:PutUserPolicy` Deny-all to force STS re-evaluation. A generic
   assistant stops at the key deactivation, leaving active sessions
   running for up to 12 hours.

3. **Task token for human approval (not Wait).** A generic assistant
   uses a fixed `Wait` state (e.g., 1 hour) which clutters the Step
   Functions dashboard and may hit the 1-year execution limit on
   long-running incidents. The skill uses the
   `sqs:sendMessage.waitForTaskToken` pattern for clean callback.

4. **No destructive actions in automation.** The skill explicitly
   refuses to include `terminate-instances` or `delete-user` in the
   automation — those are escalated to a human via the approval gate. A
   generic assistant often auto-terminates the instance, destroying
   forensic evidence.

5. **Idempotency check on quarantine SG.** The skill's Lambda checks
   if the instance is already in the quarantine SG before invoking
   `AWS-IsolateEC2Instance` — prevents double-trigger errors during a
   finding storm. A generic assistant omits this check.

6. **Audit trail via IncidentId tag propagation.** The skill tags EBS
   snapshots with `IncidentId=<uuid>` and `Preserve=true` so lifecycle
   policies do not auto-delete them. A generic assistant creates
   untagged snapshots that get cleaned up by cost-optimization rules.

## Slash-command invocation

```
/aws:automate-incident-response
```

Or via the orchestrator:

```
/aws:pipeline
You: "automate EC2 quarantine on GuardDuty severity >= 7 with a full playbook"
```

## Live-account follow-up (optional, requires AWS CLI)

After deploying the workflow, validate the posture:

```bash
# Verify the EventBridge rule is enabled
aws events describe-rule --name ir-guardduty-ec2-high-severity \
  --query 'State' --profile default

# Verify the Step Functions state machine exists and is active
aws stepfunctions describe-state-machine \
  --state-machine-arn arn:aws:states:us-east-1:111111111111:stateMachine:ir-ec2-full-playbook \
  --query 'status' --profile default

# Verify the kill-switch parameter is set
aws ssm get-parameter --name /ir/ec2-kill-switch --profile default

# Verify the quarantine SG exists in the target VPC
aws ec2 describe-security-groups \
  --group-ids sg-aaaabbbbcccc --profile default \
  --query 'SecurityGroups[0].[GroupName,VpcId]'

# Send a test event (kill-switch should be enabled for this)
aws events put-events --entries '[{
  "Source": "aws.guardduty",
  "DetailType": "GuardDuty Finding",
  "Detail": "{\"severity\": 8, \"service\": {\"serviceName\": \"guardduty\"}, \"resource\": {\"instanceDetails\": {\"instanceId\": \"i-0test12345\"}}, \"id\": \"test-finding-12345\"}"
}]' --profile default

# Verify the Step Functions execution started
aws stepfunctions list-executions \
  --state-machine-arn arn:aws:states:us-east-1:111111111111:stateMachine:ir-ec2-full-playbook \
  --max-results 1 --profile default

# Test the kill-switch: disable and verify no action
aws ssm put-parameter --name /ir/ec2-kill-switch --value "disabled" \
  --type String --overwrite --profile default
# Send another test event — workflow should succeed without action
aws ssm put-parameter --name /ir/ec2-kill-switch --value "enabled" \
  --type String --overwrite --profile default  # re-enable
```
