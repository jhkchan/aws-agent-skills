# Eval prompt: stepfunctions-full-playbook

Design a full incident response playbook. Emit the standard VERDICT block.

Finding source: guardduty
Response scope: full-playbook (isolate + snapshot + notify + recover)
Severity threshold: 7.0

Requirements:
- Orchestration: EventBridge rule -> Step Functions state machine
- State machine states (in order):
  1. CheckKillSwitch (Task: ssm:GetParameter on /ir/kill-switch)
  2. KillSwitchChoice (Choice: if "disabled" -> AbortWorkflow)
  3. ParseFinding (Task: Lambda ir-parse-finding extracts instanceId,
     incidentId, finding context)
  4. ParallelResponse (Parallel with three branches):
     - IsolateEC2 (Task: ssm:start-automation-execution:waitForTaskToken
       with AWS-IsolateEC2Instance)
     - SnapshotVolumes (Task: Lambda ir-snapshot-volumes, tags snapshots
       with IncidentId)
     - NotifySlack (Task: Lambda ir-notify-slack, posts to webhook URL
       from Parameter Store)
  5. NotifyComplete (Task: sns:Publish to ir-notifications topic)
  6. WaitForHumanApproval (Task: sqs:sendMessage.waitForTaskToken to
     ir-approval queue — human reviews and sends decision)
  7. RecoverOrClose (Choice: if decision=recover -> RecoverFromBackup,
     else CloseIncident)
  8. RecoverFromBackup (Task: Lambda ir-recover, restores from known-good
     AMI via ec2:RunInstances)
  9. CloseIncident (Succeed)
- Kill-switch: Parameter Store /ir/kill-switch checked first
- Audit: CloudTrail + Step Functions execution history (retention 90
  days) + SSM Automation execution outputs tagged with IncidentId
- IAM: each Lambda has scoped role (ec2 actions on instance ARNs, ssm on
  specific documents, sns on the IR topic, sqs on the approval queue)
- Idempotency: each Lambda checks current state before action
- Tested in security-test account (555555555555) end-to-end

Expected: AUTOMATED. The full playbook is complete, includes all safety
gates, and uses the task-token pattern for human approval (not a fixed
Wait duration).
