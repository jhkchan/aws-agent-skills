# Step Functions Failover Orchestration Patterns — Reference

This reference details the canonical failover orchestration patterns
implemented via AWS Step Functions. Each pattern includes the state
machine structure, error handling, and human-approval integration.

## Pattern 1 — Full automated failover with verification

The canonical failover orchestrator: health check -> verify primary
down -> promote secondary -> update DNS -> verify secondary up ->
notify -> human approval.

```json
{
  "StartAt": "CheckKillSwitch",
  "States": {
    "CheckKillSwitch": {
      "Type": "Task",
      "Resource": "arn:aws:states:::ssm:get-parameter",
      "Parameters": {"Name": "/dr/kill-switch"},
      "Next": "KillSwitchChoice"
    },
    "KillSwitchChoice": {
      "Type": "Choice",
      "Choices": [
        {"Variable": "$.Parameter.Value", "StringEquals": "disabled", "Next": "AbortFailover"}
      ],
      "Default": "ConfirmPrimaryDown"
    },
    "AbortFailover": {"Type": "Succeed", "Comment": "Kill-switch tripped"},
    "ConfirmPrimaryDown": {
      "Type": "Task",
      "Resource": "arn:aws:lambda:<region>:<account>:function:dr-verify-primary-down",
      "Retry": [{"ErrorEquals": ["States.TaskFailed"], "IntervalSeconds": 30, "MaxAttempts": 3, "BackoffRate": 1.5}],
      "Next": "PrimaryDownChoice"
    },
    "PrimaryDownChoice": {
      "Type": "Choice",
      "Choices": [{"Variable": "$.primaryHealthy", "BooleanEquals": true, "Next": "AbortFailover"}],
      "Default": "PromoteSecondary"
    },
    "PromoteSecondary": {
      "Type": "Task",
      "Resource": "arn:aws:lambda:<region>:<account>:function:dr-promote-secondary",
      "Catch": [{"ErrorEquals": ["States.ALL"], "Next": "NotifyFailure", "ResultPath": "$.error"}],
      "Next": "UpdateDNS"
    },
    "UpdateDNS": {
      "Type": "Task",
      "Resource": "arn:aws:states:::route53:changeResourceRecordSets",
      "Parameters": {
        "HostedZoneId": "<zone-id>",
        "ChangeBatch": {"Changes": [{"Action": "UPSERT", "ResourceRecordSet": {
          "Name": "app.example.com", "Type": "A",
          "AliasTarget": {"HostedZoneId": "Z2FDTNDATAQYW2",
            "DNSName": "secondary-alb.us-west-2.elb.amazonaws.com",
            "EvaluateTargetHealth": true}
        }}]}
      },
      "Next": "VerifySecondaryUp"
    },
    "VerifySecondaryUp": {
      "Type": "Task",
      "Resource": "arn:aws:lambda:<region>:<account>:function:dr-verify-secondary-up",
      "Next": "VerifyChoice"
    },
    "VerifyChoice": {
      "Type": "Choice",
      "Choices": [{"Variable": "$.secondaryHealthy", "BooleanEquals": true, "Next": "NotifySuccess"}],
      "Default": "RollbackDNS"
    },
    "NotifySuccess": {
      "Type": "Task",
      "Resource": "arn:aws:sns:<region>:<account>:dr-notifications",
      "Next": "WaitForHumanApproval"
    },
    "RollbackDNS": {
      "Type": "Task",
      "Resource": "arn:aws:states:::route53:changeResourceRecordSets",
      "Parameters": {
        "HostedZoneId": "<zone-id>",
        "ChangeBatch": {"Changes": [{"Action": "UPSERT", "ResourceRecordSet": {
          "Name": "app.example.com", "Type": "A",
          "AliasTarget": {"HostedZoneId": "Z2FDTNDATAQYW2",
            "DNSName": "primary-alb.us-east-1.elb.amazonaws.com",
            "EvaluateTargetHealth": true}
        }}]}
      },
      "Next": "NotifyFailure"
    },
    "NotifyFailure": {"Type": "Task", "Resource": "arn:aws:sns:<region>:<account>:dr-critical-alerts", "End": true},
    "WaitForHumanApproval": {
      "Type": "Task",
      "Resource": "arn:aws:states:::sqs:sendMessage.waitForTaskToken",
      "Parameters": {"QueueUrl": "https://sqs.<region>.amazonaws.com/<account>/dr-approval",
        "MessageBody": {"failoverId.$": "$.failoverId", "taskToken.$": "$$.Task.Token"}},
      "End": true
    }
  }
}
```

## Pattern 2 — DRS-based recovery (EC2 failover)

For Elastic Disaster Recovery, replace `PromoteSecondary` with a DRS
launch state:

```json
"LaunchDRSRecovery": {
  "Type": "Task",
  "Resource": "arn:aws:states:::drs:startRecovery.sync",
  "Parameters": {
    "SourceServerIDs.$": "$.sourceServers",
    "IsDrill": false
  },
  "Next": "UpdateDNS"
}
```

DRS launch takes 5-30 minutes. The `.sync` suffix makes Step Functions
wait for the recovery instances to be running.

## Pattern 3 — Parallel multi-component failover

For multi-tier apps (web + app + DB), use `Parallel` state:

```json
"ParallelFailover": {
  "Type": "Parallel",
  "Next": "UpdateDNS",
  "Branches": [
    {
      "StartAt": "FailoverDB",
      "States": {
        "FailoverDB": {
          "Type": "Task",
          "Resource": "arn:aws:lambda:<region>:<account>:function:dr-failover-aurora",
          "End": true
        }
      }
    },
    {
      "StartAt": "ScaleOutASG",
      "States": {
        "ScaleOutASG": {
          "Type": "Task",
          "Resource": "arn:aws:states:::autoscaling:updateAutoScalingGroup",
          "Parameters": {
            "AutoScalingGroupName": "warm-standby-asg",
            "DesiredCapacity": 20,
            "MinSize": 10
          },
          "End": true
        }
      }
    }
  ]
}
```

DB failover and ASG scale-out run in parallel — both must complete
before DNS update.

## Pattern 4 — Distributed Map for fleet failover

For large fleets (100+ EC2 instances), use Distributed Map:

```json
"FailoverAllInstances": {
  "Type": "Map",
  "ItemsPath": "$.instanceIds",
  "MaxConcurrency": 10,
  "Iterator": {
    "StartAt": "LaunchOne",
    "States": {
      "LaunchOne": {
        "Type": "Task",
        "Resource": "arn:aws:states:::drs:startRecovery.sync",
        "Parameters": {
          "SourceServerIDs.$": "States.Array($)"
        },
        "End": true
      }
    }
  },
  "Next": "UpdateDNS"
}
```

`MaxConcurrency: 10` prevents overwhelming the DRS API. Adjust based on
API throttle limits.

## Error handling patterns

### Retry with backoff

```json
"Retry": [
  {
    "ErrorEquals": ["States.TaskFailed", "Lambda.ServiceException"],
    "IntervalSeconds": 30,
    "MaxAttempts": 3,
    "BackoffRate": 1.5
  }
]
```

### Catch and rollback

```json
"Catch": [
  {
    "ErrorEquals": ["States.ALL"],
    "Next": "RollbackDNS",
    "ResultPath": "$.error"
  }
]
```

### Timeout per state

```json
"PromoteSecondary": {
  "Type": "Task",
  "Resource": "...",
  "TimeoutSeconds": 900,
  "Next": "UpdateDNS"
}
```

15-minute timeout on DB promotion. If promotion does not complete in
15 minutes, the state fails and triggers the catch -> rollback.

## Human approval integration

### SQS task token (preferred)

The workflow sends a message to an SQS queue with the task token. A
human (or approval Lambda) reads the queue, makes a decision, and calls
`SendTaskSuccess` or `SendTaskFailure` with the token.

```python
# Approval Lambda
import boto3
sfn = boto3.client('stepfunctions')

def lambda_handler(event, context):
    task_token = event['taskToken']
    decision = event['decision']  # 'approve' or 'reject'
    if decision == 'approve':
        sfn.send_task_success(taskToken=task_token, output='{"approved": true}')
    else:
        sfn.send_task_failure(taskToken=task_token, error='Rejected', cause='Human rejected')
```

### CLI approval

```bash
aws stepfunctions send-task-success \
  --task-token <token-from-sqs> \
  --task-output '{"approved": true}'
```

## State machine deployment

```bash
aws stepfunctions create-state-machine \
  --name dr-failover-orchestrator \
  --definition file://failover.asl.json \
  --role-arn arn:aws:iam::<account>:role/StepFunctionsDRFailoverRole \
  --type STANDARD
```

Use `STANDARD` (not `EXPRESS`) — failover executions may run for hours
(human approval gate). EXPRESS has a 5-minute max.

## IAM role for the state machine

The Step Functions execution role needs:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {"Effect": "Allow", "Action": ["lambda:InvokeFunction"], "Resource": "arn:aws:lambda:*:*:function:dr-*"},
    {"Effect": "Allow", "Action": ["route53:ChangeResourceRecordSets"], "Resource": "arn:aws:route53:::hostedzone/*"},
    {"Effect": "Allow", "Action": ["sns:Publish"], "Resource": "arn:aws:sns:*:*:dr-*"},
    {"Effect": "Allow", "Action": ["sqs:SendMessage"], "Resource": "arn:aws:sqs:*:*:dr-*"},
    {"Effect": "Allow", "Action": ["ssm:GetParameter"], "Resource": "arn:aws:ssm:*:*:parameter/dr/*"},
    {"Effect": "Allow", "Action": ["drs:StartRecovery", "drs:DescribeRecoveryInstances"], "Resource": "*"},
    {"Effect": "Allow", "Action": ["rds:FailoverGlobalCluster", "rds:RemoveFromGlobalCluster"], "Resource": "*"}
  ]
}
```

Scope to specific resources where possible. Avoid `Resource: "*"` for
production deployments.
