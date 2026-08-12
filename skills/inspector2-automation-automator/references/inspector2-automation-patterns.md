# Inspector2 Automation Patterns Reference

Supplementary reference for the Inspector2 Automation Automator
skill. Use when selecting an automation pattern, designing the
EventBridge rule, or debugging a workflow that did not fire.

## Automation pattern matrix

| Pattern | Severity | Resource | Reversible | Notes |
|---|---|---|---|---|
| SNS notify only | Any | Any | Yes | Slack/email; reporting only |
| SSM patch (EC2 OS) | Critical | `AwsEc2Instance` | Yes (snapshot rollback) | `AWS-RunPatchBaseline` Install |
| SSM patch via maintenance window | Medium/High | `AwsEc2Instance` | Yes | Scheduled; not event-driven |
| ECR image rebuild | Critical/High | `AwsEcrContainerImage` | Yes (rollback tag) | CodeBuild trigger |
| Lambda function update | Critical/High | `AwsLambdaFunction` | Yes (version rollback) | CI/CD required |
| Finding suppression | Any | Any | Yes (re-open) | Document rationale |
| Security Hub forwarding | All | Any | Yes | One-way Inspector → SecHub |
| Custom EventBridge → Lambda | Any | Any | Varies | Full Lambda power |

## EventBridge event patterns

### Critical EC2 finding → SSM patch

```json
{
  "source": ["aws.inspector2"],
  "detail-type": ["Inspector Finding"],
  "detail": {
    "severity": ["CRITICAL"],
    "status": ["OPEN"],
    "resources": {
      "type": ["AWS_EC2_INSTANCE"]
    }
  }
}
```

### Critical ECR finding → CodeBuild rebuild

```json
{
  "source": ["aws.inspector2"],
  "detail-type": ["Inspector Finding"],
  "detail": {
    "severity": ["CRITICAL", "HIGH"],
    "status": ["OPEN"],
    "resources": {
      "type": ["AWS_ECR_CONTAINER_IMAGE"]
    }
  }
}
```

### Lambda code scan finding → notify

```json
{
  "source": ["aws.inspector2"],
  "detail-type": ["Inspector Finding"],
  "detail": {
    "severity": ["CRITICAL", "HIGH", "MEDIUM"],
    "status": ["OPEN"],
    "resources": {
      "type": ["AWS_LAMBDA_FUNCTION"]
    }
  }
}
```

## SSM patch baseline parameters

| Parameter | Value | Purpose |
|---|---|---|
| `Operation` | `Scan` / `Install` | Scan = read-only; Install = patches |
| `RebootOption` | `RebootIfNeeded` / `NoReboot` | Reboot after patch |
| `SnapshotId` | empty string | Required param even when empty |
| `InstanceId` | `i-0abc123...` | Single instance |
| `InstanceIds` | list | Multiple instances (custom runbook only) |

**Patch baseline gotchas:**
- `Operation: Scan` populates the SSM compliance dashboard. It
  does NOT modify the instance.
- `Operation: Install` applies patches and may reboot. Always run
  after `Scan` validates baseline contents.
- `RebootOption: NoReboot` leaves patches in `InstalledPendingReboot`
  state. Use `RebootIfNeeded` for production patches.

## Inspector finding lifecycle

```
OPEN ─┬─> (auto-resolved post-rescan) ─> CLOSED
      │
      ├─> (suppressed with reason) ─> SUPPRESSED ─> (finding changes) ─> OPEN
      │
      └─> (manually closed — anti-pattern) ─> CLOSED (drift)
```

**Lifecycle rules:**
- Inspector auto-closes findings when the underlying vulnerability
  is no longer detected post-rescan.
- Suppression marks `status: SUPPRESSED` but does NOT close the
  finding.
- Suppressed findings re-open if the finding changes (e.g., new
  evidence, severity bump).
- Manual close creates drift between Inspector and Security Hub —
  do NOT manually close.

## Security Hub integration

| Direction | Latency | Notes |
|---|---|---|
| Inspector → Security Hub | ~5 minutes | Auto when both enabled |
| Security Hub → Inspector | NOT supported | Inspector is source of truth |

**Integration rules:**
- Closing an Inspector finding closes the Security Hub finding
  within 5 minutes.
- Suppressing an Inspector finding sets SecHub workflow status to
  `SUPPRESSED`.
- Inspector-generated SecHub findings have
  `ProductArn: arn:aws:securityhub:<region>::product/aws/inspector`.

## Execution role requirements

### EventBridge → SSM direct invoke

The EventBridge target role needs:

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {"Service": "events.amazonaws.com"},
    "Action": "sts:AssumeRole"
  }]
}
```

Policy: `ssm:StartAutomationExecution` on the runbook ARN.

### EventBridge → Lambda

Lambda needs a DLQ and async invocation config:

```bash
aws lambda put-function-event-invoke-config \
  --function-name inspector-finding-triage \
  --maximumRetryAttempts 2 \
  --maximumEventAgeInSeconds 3600 \
  --destination-config '{"OnFailure":{"Destination":"arn:aws:sqs:us-east-1:111111111111:inspector-finding-dlq"}}'
```

### Inspector delegated admin role

In the delegated admin account, Inspector needs:

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Action": ["inspector2:*", "securityhub:BatchImportFindings"],
    "Resource": "*"
  }]
}
```

Plus `organizations:DescribeOrganization`, `organizations:ListAccounts`
for multi-account coverage queries.

## Common automation failures and fixes

| Failure | Root cause | Fix |
|---|---|---|
| EventBridge rule never fires | Event pattern mismatch (e.g., `detail-type` wrong) | Verify with `aws events test-event-pattern` |
| Lambda throttled on finding burst | Concurrent invocation limit | Add SQS buffer or use step function |
| SSM patch fails with `ACCESS_DENIED` | Instance profile missing `AmazonSSMManagedInstanceCore` | Attach the managed policy |
| Finding stays OPEN after patch | Rescan not triggered; baseline incomplete | Trigger `aws inspector2 batch-get-finding-details` to verify |
| Security Hub finding stays OPEN | 5-minute propagation delay | Wait; verify with `securityhub get-findings` |
| Suppression does not stick | Finding `updatedAt` changed (re-evaluated) | Re-suppress with new rationale |
| CodeBuild rebuild loop | EventBridge fires on the rebuilt image's finding | Filter event by tag `env=prod-canary` or add lock |
| ECR image scan returns stale | Scan is push-time; new CVEs need rescan | Schedule weekly `start-image-scan` |
