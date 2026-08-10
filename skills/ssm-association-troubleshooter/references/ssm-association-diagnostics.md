# SSM Association Diagnostics Reference

Supplementary reference for the SSM Association Troubleshooter
skill. Use when diagnosing association failures, picking the right
diagnostic command, interpreting SSM agent log entries, or
mapping a symptom to its root cause.

## Diagnostic commands (quick lookup)

| Command | Use | Key fields |
|---|---|---|
| `aws ssm describe-instance-information` | Instance coverage + agent state | `PingStatus`, `LastPingDateTime`, `AgentVersion`, `IsLatestVersion`, `PlatformType`, `IamRoleARN` |
| `aws ssm list-associations` | All associations for an instance / region | `Status`, `LastExecutionDate`, `Overview` |
| `aws ssm describe-association` | Single-association config + targets | `State`, `ScheduleExpression`, `Targets`, `OutputLocation` |
| `aws ssm describe-instance-associations-status` | Per-instance association execution state | `Status`, `ExecutionTime`, `DetailedStatus`, `ErrorCount` |
| `aws ssm describe-association-executions` | Detailed execution history | `ExecutionId`, `Status`, `StatusMessage`, `ResourceStatusSummary` |
| `aws ssm describe-association-execution-targets` | Per-target results within an execution | `Status`, `StatusMessage`, `ResourceId`, `OutputSource.S3Url` |
| `aws ssm list-association-versions` | Association change history | `Version`, `Parameters`, `ScheduleExpression` per version |
| `aws ssm describe-document` | Document metadata + versions | `LatestVersion`, `DefaultVersion`, `PlatformTypes`, `SchemaVersion` |
| `aws ssm describe-patch-baseline` | Patch baseline approval rules | `ApprovalRules`, `OperatingSystem`, `GlobalFilters` |
| `aws ssm describe-patch-states` | Per-instance patch compliance state | `PatchGroup`, `ComplianceStatus`, `MissingCount`, `InstalledPendingCount` |
| `aws ssm list-compliance-items` | Per-resource compliance (patch + assoc) | `ComplianceType`, `Status`, `Severity` |
| `aws ssm describe-activations` | Hybrid activation metadata | `ActivationId`, `IamRole`, `Expired`, `RegistrationLimit` |
| `aws ssm list-command-invocations` | Per-command execution detail | `Status`, `StatusDetails`, `NotificationStatus` |
| `aws ssm get-command-invocation` | Detailed per-instance command output | `StandardOutputContent`, `StandardErrorContent` |
| `aws ec2 describe-instances` | EC2 metadata, profile, state | `State.Name`, `IamInstanceProfile.Arn`, `LaunchTime` |
| `aws ec2 describe-vpc-endpoints` | SSM VPC endpoints for private subnets | `ServiceName`, `State`, `SubnetIds` |
| `aws iam simulate-principal-policy` | Test IAM permissions without policy change | `EvalDecision`, `MatchedStatements` |

## Association execution status values

| Status | Meaning | Action |
|---|---|---|
| `Success` | Document orchestration completed (per-target may still fail) | Verify per-target via `describe-association-execution-targets` |
| `Failed` | Orchestration-level failure (e.g., target unreachable, parameter invalid) | Inspect `StatusMessage`; drill into targets |
| `TimedOut` | Execution exceeded `ExecutionTimeout` or agent unreachable | 3-layer health check |
| `Pending` | In-flight — not yet complete | Re-check after schedule window |
| `Cancelled` | Operator cancelled mid-run | Confirm intentional |

## Per-target status values (the source of truth)

A `Success` association can have per-target `Failed`. Always read
`describe-association-execution-targets` for the actual result:

| Target Status | Meaning | Evidence source |
|---|---|---|
| `Success` | Document script ran and returned 0 | `OutputSource.S3Url` stdout |
| `Failed` | Script returned non-zero, or AccessDenied, or resource not found | `StatusMessage` + S3 stderr |
| `TimedOut` | Per-target timeout (script hung) | Agent log plugin entry |
| `Cancelled` | Operator cancelled | CloudTrail `CancelCommand` |

## Common error signatures (from StatusMessage / agent log)

| Signature | Layer | Root cause | Fix |
|---|---|---|---|
| `InvalidInstanceId` | Agent | Instance not registered or rate-limited (concurrency) | Wait + retry; or run 3-layer check |
| `TargetNotConnected` | Connectivity | Agent offline / network blocked | 3-layer check |
| `AccessDenied` on `s3:PutObject` | IAM | Role lacks output-bucket permission | Add `s3:PutObject` for bucket |
| `AccessDenied` on `ssm:*` | IAM | Role lacks `AmazonSSMManagedInstanceCore` | Attach policy |
| `InvalidDocument` | Document | Document deleted or name typo | Recreate / fix association |
| `InvalidParameters` | Document | Parameter schema mismatch | Fix parameters; check document version |
| `DocumentVersionDoesNotExist` | Document | Association pinned to deleted version | Update `DocumentVersion` |
| `TimeoutExceeded` | Document | Script hung or `timeoutSeconds` too low | Add explicit timeout; debug script |
| `AssociationDoesNotExist` | Association | Wrong association-id | Verify via `list-associations` |
| `ThrottlingException` | SSM service | Rate limited (concurrent associations or commands) | Stagger schedules |
| `EmptyInstanceID` | Agent | New instance still bootstrapping | Wait 5-10 min |
| `AssociationVersionLimitExceeded` | Association | > 99 versions; SSM pruned old versions | Recreate association |

## Schedule expression syntax

SSM associations support two formats:

| Format | Example | Meaning |
|---|---|---|
| `rate(N unit)` | `rate(1 day)` | Every N units (minutes/hours/days) |
| `cron(...)` | `cron(0 2 * * ? *)` | AWS cron (6-field with `?`) |

**Cron field order:** minutes, hours, day-of-month, month,
day-of-week, year (optional).

**SSM cron rules:**
- `?` is REQUIRED in either day-of-month or day-of-week (mutually
  exclusive fields). Setting both produces a validation error.
- `*` means "every"; `?` means "no specific value".
- `0 2 * * ? *` = 02:00 UTC daily (correct)
- `0 2 * * *` = INVALID for SSM (both DOM and DOW set)

**Common cron patterns:**

| Cron | Schedule |
|---|---|
| `cron(0 2 * * ? *)` | Daily at 02:00 UTC |
| `cron(0 0 * * SUN *)` | Sundays at 00:00 UTC |
| `cron(0,30 * * * ? *)` | Every 30 minutes |
| `cron(0 0 1 * ? *)` | First of every month at 00:00 UTC |

## Targets reference

Association targets are evaluated at execution time, not creation.

| Target key | Example values | Behavior |
|---|---|---|
| `InstanceIds` | `i-0abc123def` | Explicit list (max 50) |
| `tag:<key>` | `Key=tag:Environment,Values=prod` | All instances with matching tag |
| `tag:<key>` with `>` | `Key=tag:Owner,Values=team-a>` | Hierarchical match |
| `ResourceGroups:ResourceTypeFilters` | `AWS::EC2::Instance` | Resource-group-based |
| `ParameterValues` | From SSM Parameter Store | Dynamic target list |

**Tag-key matching is case-sensitive.** `Key=tag:Patch Group` (with
space, capital G) is different from `Key=tag:patch group`. Verify
the exact tag key in `ec2 describe-instances --query
Reservations[*].Instances[*].Tags`.

## Patch baseline compliance states

| ComplianceStatus | Meaning |
|---|---|
| `COMPLIANT` | All required patches installed |
| `NON_COMPLIANT` | At least one approved patch missing |
| `UNSPECIFIED` | No baseline applied (no `Patch Group` tag, no default) |

Per-patch `InstalledPending` means installed but awaiting reboot
(Windows). `Missing` means not installed. Both count toward
`NON_COMPLIANT`.

## IAM actions needed by SSM (per association type)

| Association type | Required additional actions |
|---|---|
| `AWS-ApplyPatchBaseline` | None (uses SSM service role) |
| `AWS-GatherSoftwareInventory` | None (uses SSM service role) |
| `AWS-UpdateSSMAgent` | None |
| `AWS-RunShellScript` / `AWS-RunPowerShellScript` | Varies by script |
| Custom document calling AWS APIs | The specific API actions the script calls |
| Document with S3 output | `s3:PutObject`, `s3:GetObject`, `s3:ListBucket` on the output bucket |
| Document with CloudWatch Logs | `logs:CreateLogStream`, `logs:PutLogEvents` |

The base `AmazonSSMManagedInstanceCore` policy covers core SSM
operations but NOT S3 output bucket writes or CloudWatch Logs.
Add an inline or managed policy for these.

## Diagnostic flowchart (high-level)

```
START: association problem reported
│
├─ Instance shows in describe-instance-information?
│  ├─ No → Step 4 (NotManaged) — run 3-layer check
│  └─ Yes → Continue
│
├─ Association exists in list-associations?
│  ├─ No → Association was deleted; recreate
│  └─ Yes → Continue
│
├─ Association State = ENABLED?
│  ├─ No → Step 5 (NeverRuns) — update-association-state
│  └─ Yes → Continue
│
├─ describe-association-executions shows recent runs?
│  ├─ No → Step 5 (NeverRuns) — schedule/target issue
│  └─ Yes → Continue
│
├─ Execution Status?
│  ├─ Failed → Step 2 — drill into StatusMessage + S3 output
│  ├─ TimedOut → Step 3 — 3-layer check + script timeout
│  └─ Success → Check per-target Status (Step 6 — document error)
│
└─ Per-target Status?
   ├─ Failed → Step 6 — script error / permission / platform
   ├─ TimedOut → Step 3 — script hang
   └─ Success → True success; investigate next layer (e.g., patch
                compliance is separate from association success)
```

## CloudTrail events for SSM diagnosis

| EventName | What it tells you |
|---|---|
| `StartAssociationsOnce` | Operator triggered an association run manually |
| `StartExecution` (Automation) | Automation runbook started |
| `SendCommand` | Operator sent a one-off command |
| `CreateAssociation` / `UpdateAssociation` | Config change |
| `ThrottlingException` | Rate limiting (visible in CloudTrail Insights) |
| `AccessDenied` | IAM permission gap (visible in event `errorMessage`) |

For deeper diagnosis, query CloudTrail for the relevant time
window:

```bash
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=EventName,AttributeValue=UpdateAssociation \
  --start-time $(date -u -v-1H +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --query 'Events[*].[EventTime,Username,ResourceName]' --output table
```
