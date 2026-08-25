# Incident Response Automator — advanced patterns (moved verbatim from SKILL.md)

> Progressive-disclosure split: this content was moved verbatim from SKILL.md; nothing was rewritten.

## Mindset — extended rationale (three facts)

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

## Orchestration surface selection — detailed notes

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

## GuardDuty EventBridge event pattern (severity >= 7)

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

## Security Hub EventBridge event pattern

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

## CloudWatch alarm EventBridge event pattern

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

## AWS Health EventBridge event pattern

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

## Full-playbook Step Functions state machine (ASL)

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

## Map state — parallel containment across multiple resources

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
