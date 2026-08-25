---
name: ssm-session-troubleshooter
description: 'Diagnoses AWS Systems Manager Session Manager failures through a thirteen-category diagnostic tree: managed instance not showing up (SSM Agent not running, activation code expired, hybrid enrollment), session connection timeout (ssmmessages endpoint, Security group egress), SSM Agent version outdated (session features require minimum agent version), IAM role missing ssm:StartSession / ssm:TerminateSession / ssm:ResumeSession (AmazonSSMManagedInstanceCore), VPC endpoint for SSM missing one of the three required endpoints (ssm, ec2messages, ssmmessages), session document errors (SSM_Session document schema or sharing), port forwarding failures (local-port-forwarding document and target-host reachability), shell profile errors (SSM-SessionManagerRunShell profile misconfig), audit log delivery to S3 missing (S3 bucket policy for session-output), session recording to S3 (encryption and bucket Region), CloudWatch Logs delivery missing (log group permission on the instance role), macOS vs Linux agent...'
license: Apache-2.0
compatibility: Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). Offline symptom classification works from pasted error messages and instance configuration. Live-account diagnosis uses aws ssm describe-instance-information, describe-sessions, get-document, describe-instance-properties, aws ec2 describe-instances / describe-vpc-endpoints / describe-security-groups, aws iam simulate-principal-policy on the instance role, aws logs describe-log-groups / filter-log-events, aws...
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: 'true'
  phase: '2'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: Management
  task_type: troubleshoot
  skill_class: capability
  lifecycle_status: active
  verdict_shape: ROOT_CAUSE_IDENTIFIED | INSUFFICIENT_DATA
  when_to_use: Diagnosing an SSM Session Manager failure (managed instance not showing in the console, session connection timeout, port forwarding failure, "is not registered to the account or role" error, missing audit logs in S3, missing CloudWatch Logs, session recording failure, shell profile error, patch-baseline-blocked session, SSM Document error, agent version too old for session features), walking a symptom to the failed layer with verify and fix commands, validating why a session cannot start or connect, or triaging a "Session Manager is broken" page where the root cause may be agent, IAM role, VPC endpoint, document, shell profile, or audit-log config — not necessarily the SSM service itself.
  when_not_to_use: SSM Run Command / Automation execution debugging (use ssm-automation-deployer or a run-command skill), EC2 instance reachability at the OS level (use ec2-instance-reachability checks), patch compliance posture audits (use ssm-patch-compliance-automator), or IAM policy authoring for the instance role (use iam-least-privilege-advisor). This skill diagnoses Session Manager connectivity and session-output failures; it does not audit patch baseline posture or debug Run Command document execution.
  activation_triggers: SSM Session Manager connection failed, SSM session timeout, managed instance not showing up, instance not registered SSM, SSM Agent not running, ssm:StartSession denied, SSM port forwarding failed, channel closed Session Manager, ssmmessages endpoint, VPC endpoint SSM missing, SSM session recording S3, SSM audit logs missing, SessionManagerRunShell, SSM Document error, SSM agent version outdated, hybrid activation expired, patch baseline blocking session, troubleshoot SSM Session Manager
  invocation_schema: 'Input: either (a) a symptom description (error message, observed behaviour, "session times out after 10s", "instance not in the console"), optionally paired with the instance configuration (describe-instance-information output) and recent SSM / CloudWatch logs, OR (b) an InstanceId plus session context (document name, session id, target host for port forwarding, VPC endpoint config) for live-account diagnosis. Output: a deterministic TARGET/VERDICT/REASON/LAYER/EVIDENCE/REMEDIATION block where VERDICT ∈ {ROOT_CAUSE_IDENTIFIED, INSUFFICIENT_DATA} and LAYER ∈ {INSTANCE_NOT_REGISTERED, SESSION_CONNECTION_TIMEOUT, AGENT_OUTDATED, IAM_PERMISSION_MISSING, VPC_ENDPOINT_MISSING, SESSION_DOCUMENT_ERROR, PORT_FORWARDING_FAILURE, SHELL_PROFILE_ERROR, AUDIT_LOG_S3_MISSING, SESSION_RECORDING_S3, CLOUDWATCH_LOGS_MISSING, PATCH_BASELINE_BLOCKING, SSM_DOCUMENT_ERROR, UNKNOWN}.'
  invocation_example: '# Minimal valid input (offline symptom classification):

    Symptom: "EC2 instance i-0abcdef1234567890 in a private subnet does

    not appear in the SSM Fleet Manager console. The instance

    has the AmazonSSMManagedInstanceCore role attached but is

    in a VPC with no ssmmessages VPC endpoint. Sessions started

    from other instances in a public subnet work fine."

    InstanceId: i-0abcdef1234567890

    VPC: vpc-priv (no internet gateway, no NAT gateway)

    InstanceRole: EC2-SSM-Role (AmazonSSMManagedInstanceCore attached)

    VPC endpoints configured: ssm (interface), ec2messages (interface)

    VPC endpoints MISSING: ssmmessages

    Last log line: "Session Manager connection timed out"'
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  keywords: SSM, Session Manager, ssm:StartSession, SSM Agent, AmazonSSMManagedInstanceCore, VPC endpoint, ssmmessages, ec2messages, port forwarding, shell profile, session recording, S3 audit logs, CloudWatch Logs, hybrid enrollment, activation code, patch baseline, SSM Document, troubleshooting
  tags: ssm, management, troubleshooting, session-manager, vpc-endpoint, iam-role, port-forwarding, session-recording, audit-logs
---

# SSM Session Troubleshooter

## Quick start

- **Symptom → layer map (first plausible match drives the first probe):**
  instance not in Fleet Manager console → INSTANCE_NOT_REGISTERED
  / AGENT_OUTDATED; session times out after starting →
  SESSION_CONNECTION_TIMEOUT / VPC_ENDPOINT_MISSING;
  `AccessDeniedException` on StartSession → IAM_PERMISSION_MISSING;
  port forwarding fails to connect → PORT_FORWARDING_FAILURE /
  SESSION_CONNECTION_TIMEOUT; `ChannelClosedException` /
  shell-profile errors → SHELL_PROFILE_ERROR; session output not
  in S3 → AUDIT_LOG_S3_MISSING / SESSION_RECORDING_S3; CloudWatch
  Logs missing → CLOUDWATCH_LOGS_MISSING; session fails during
  maintenance window → PATCH_BASELINE_BLOCKING; document schema
  error → SESSION_DOCUMENT_ERROR / SSM_DOCUMENT_ERROR.
> Moved to [references/advanced-patterns.md](references/advanced-patterns.md#quick-start--verification-and-coverage-rules).
> Probe-driven verdicts, the three-endpoint rule for private subnets (missing ssmmessages = session timeouts), AmazonSSMManagedInstanceCore ssmmessages actions, agent version gates (2.3.68.0 sessions / 3.0.196 port-forwarding / 3.1.x macOS).

## Mindset

> Moved to [references/advanced-patterns.md](references/advanced-patterns.md#mindset).
> SSM service is usually innocent: the broken layer is agent, instance-role IAM, one of the three VPC endpoints, the session document, the shell profile, or the audit-log bucket policy. Start with describe-instance-information, describe-vpc-endpoints, and simulate-principal-policy.

## Philosophy

> Moved to [references/advanced-patterns.md](references/advanced-patterns.md#philosophy).
> Control plane (ssm) vs data plane (ssmmessages) vs ec2messages; registration != session-ready; role gates StartSession AND ssmmessages data channel; session output configured at the document level, not the instance level.

## Quick reference — symptom triage table

| Symptom phrase / error | Most likely layer | First probe |
|---|---|---|
| Instance absent from Fleet Manager / `describe-instance-information` returns empty | INSTANCE_NOT_REGISTERED | `describe-instance-information`, EC2 userdata / agent install log |
| Instance `PingStatus: ConnectionLost` / `InActive` | INSTANCE_NOT_REGISTERED / AGENT_OUTDATED | `describe-instance-information` AgentVersion, LastPingDateTime |
| Session starts on client, then "Connection timed out" / `ChannelClosedException` | SESSION_CONNECTION_TIMEOUT / VPC_ENDPOINT_MISSING | `describe-vpc-endpoints` for ssm/ec2messages/ssmmessages; SG egress to endpoints |
| `AccessDeniedException` on `start-session` CLI call (caller side) | IAM_PERMISSION_MISSING (caller) | `iam simulate-principal-policy` on the caller's role for `ssm:StartSession` |
| Session starts, agent log shows `ssmmessages:OpenDataChannel AccessDenied` | IAM_PERMISSION_MISSING (instance role) | `iam simulate-principal-policy` on the instance role for `ssmmessages:OpenDataChannel` |
| Port forwarding connects but target host unreachable | PORT_FORWARDING_FAILURE | `ssm start-session` document name, target host reachability from the instance |
| Port forwarding fails with `NotSupported` on the agent | AGENT_OUTDATED | `describe-instance-information` AgentVersion < 3.0.196 |
| `InvalidDocument` or `InvalidDocumentVersion` on session start | SESSION_DOCUMENT_ERROR / SSM_DOCUMENT_ERROR | `ssm get-document --name SSM-SessionManagerRunShell` |
| Session opens, exits immediately, `amazon-ssm-agent.log` shows shell profile error | SHELL_PROFILE_ERROR | agent log for `SessionTypeHandler` / profile errors |
| Sessions work but no JSON output in the S3 session bucket | AUDIT_LOG_S3_MISSING | `get-document` S3 bucket, `get-bucket-policy` for ssm-output grant |
| Session recording missing from S3; shell scrollback truncated | SESSION_RECORDING_S3 | document `s3BucketName`, KMS key policy, bucket Region |
| Sessions work but CloudWatch Logs group is empty | CLOUDWATCH_LOGS_MISSING | document `cloudWatchLogGroupName`, role `logs:CreateLogStream` |
| Sessions fail during a maintenance window; `ScanOnly` association in `Running` state | PATCH_BASELINE_BLOCKING | `describe-association`, `describe-instance-associations-status` |
| macOS instance cannot start session; agent installed but session API errors | AGENT_OUTDATED | AgentVersion < 3.1.x for macOS session support |
| None of the above; region-wide SSM event | INSUFFICIENT_DATA | `aws health describe-events`, AWS Service Health Dashboard |

## Pre-flight: instance and session state

Gather the canonical configuration and short-circuit on instance
states that mimic session failures. Misclassifying these produces
hours of session debugging for a problem that is not a session
problem.

> Moved to [references/diagnostic-commands.md](references/diagnostic-commands.md#pre-flight-probes-instance-and-session-state).
> Eight probes: describe-instance-information / -properties, describe-sessions, get-document, instance-role simulate-principal-policy (ssm + ssmmessages + s3/logs actions), describe-vpc-endpoints, security-group egress, agent-log filter, AWS Health.

### Instance-state short-circuit

| `PingStatus` / `describe-instance-information` | Effect on diagnosis |
|---|---|
| `Online` + recent `LastPingDateTime` | Agent control channel works; if sessions fail, the issue is data channel, IAM, document, or network — not registration. |
| `ConnectionLost` / `InActive` | Agent stopped, instance stopped, or network break. The instance will not appear in Fleet Manager. Start at INSTANCE_NOT_REGISTERED. |
| Instance absent from `describe-instance-information` | Either the agent is not installed/running, the instance role lacks `ssm:UpdateInstanceInformation`, or the instance cannot reach `ssm.*.amazonaws.com`. Start at INSTANCE_NOT_REGISTERED. |
| `AgentVersion: 2.x.x` (below 2.3.68) | Session Manager not supported on this agent version. Sessions fail with `NotSupported` or silently. AGENT_OUTDATED. |
| `AgentVersion: 3.0.x` below 3.0.196 | Port forwarding not supported. PORT_FORWARDING_FAILURE due to AGENT_OUTDATED. |
| `PlatformName: Mac OS` + agent below 3.1.x | Session Manager not supported on macOS below 3.1. AGENT_OUTDATED. |

If input is malformed (missing InstanceId, absent symptom
description, no document name for document errors), emit:

```text
TARGET: <instance-id or unknown>
VERDICT: INSUFFICIENT_DATA
REASON: Input is missing required context — at minimum a symptom
  description (error string or observed behaviour) and the
  InstanceId, plus for document/output errors the session document
  name and the target S3 bucket or CloudWatch log group.
LAYER: UNKNOWN
EVIDENCE:
  - Missing: <list specific missing fields>
REMEDIATION: Re-prompt for: (1) the exact error string or observed
  symptom, (2) the InstanceId and platform (Linux / macOS /
  Windows), (3) the instance VPC and whether it has internet
  access, and (4) for output/audit errors, the session document
  name and the target S3 bucket / CloudWatch log group.
```

## Process — Diagnostic decision tree (apply in symptom order)

Symptom-driven. Pick the entry point based on the observed symptom,
then walk the layer-specific probes in order. **Never emit
ROOT_CAUSE_IDENTIFIED without a failing probe that matches the
symptom.**

### Step 0: Non-obvious behaviours that change diagnosis

> Moved to [references/advanced-patterns.md](references/advanced-patterns.md#step-0-non-obvious-behaviours-that-change-diagnosis).
> Three-endpoint rule, StartSession on the caller vs ssmmessages on the instance, AmazonEC2RoleforSSM deprecation, agent version floors and self-update via S3, document-carried audit config, shell-profile instant-close, hybrid activation expiry, patch associations slowing the data channel, macOS agent differences, stale Active sessions.

### Step 1: Instance registration layer

Entry: instance absent from Fleet Manager /
`describe-instance-information` returns empty for the instance.

1. **Is the instance running and does it have an instance profile?**
   ```bash
   aws ec2 describe-instances --instance-ids <i-id> \
     --query 'Reservations[0].Instances[0].[State.Name,IamInstanceProfile.Arn]' --output text
   ```
   - State `stopped` → start the instance first.
   - No instance profile ARN → the role is missing; attach one.
     **INSTANCE_NOT_REGISTERED.**

2. **Does the instance role include AmazonSSMManagedInstanceCore?**
   ```bash
   aws iam list-attached-role-policies --role-name <role-name> --output json
   ```
   - AmazonSSMManagedInstanceCore NOT attached → the agent cannot
     call `ssm:UpdateInstanceInformation`. **INSTANCE_NOT_REGISTERED.**
   - Legacy `AmazonEC2RoleforSSM` → deprecated; switch to
     AmazonSSMManagedInstanceCore.

3. **Can the agent reach the SSM endpoint?**
   - Public subnet: route to IGW; agent reaches `ssm.<region>.amazonaws.com`.
   - Private subnet with NAT: route to NAT; agent reaches the
     public SSM endpoint.
   - Private subnet without NAT: needs `ssm`, `ec2messages`, and
     `ssmmessages` interface VPC endpoints.
   - VPC endpoint missing → agent never registers.
     **INSTANCE_NOT_REGISTERED (network).**

4. **Is the SSM Agent running on the instance?**
   On the instance:
   ```bash
   sudo systemctl status amazon-ssm-agent          # Linux systemd
   sudo launchctl list | grep amazon-ssm-agent     # macOS
   Get-Service AmazonSSMAgent                       # Windows PowerShell
   ```
   - Agent not installed or stopped → install or start it.
     **INSTANCE_NOT_REGISTERED.**

5. **For hybrid (non-EC2) instances: is the activation valid?**
   ```bash
   aws ssm describe-activations --output json
   ```
   - `ExpiredDate` in the past or `RegistrationLimit` reached →
     the agent cannot re-register after a restart.
     **INSTANCE_NOT_REGISTERED (hybrid).**

If the instance is running, the role is correct, the agent is
installed, but registration still fails, move to the VPC endpoint
layer (Step 5) — the agent may not be reaching `ssm.*`.

### Step 2: IAM permission layer (instance role)

Entry: session starts on the client then times out, or agent log
shows `ssmmessages:OpenDataChannel AccessDenied`.

```bash
aws iam simulate-principal-policy \
  --policy-source-arn "<instance-role-arn>" \
  --action-names ssm:UpdateInstanceInformation \
    ssmmessages:CreateControlChannel ssmmessages:CreateDataChannel \
    ssmmessages:OpenControlChannel ssmmessages:OpenDataChannel \
    s3:PutObject logs:CreateLogStream \
  --output json
```

- Any action that returns `implicitDeny` or `explicitDeny` confirms
  the role is missing the permission. **IAM_PERMISSION_MISSING.**
- `ssmmessages:OpenDataChannel` denied → session times out within
  seconds of starting on the client.
- `s3:PutObject` on the session-output bucket denied → sessions
  work but audit logs never land in S3. Cross-reference Step 7.
- `logs:CreateLogStream` denied → sessions work but CloudWatch
  Logs group stays empty. Cross-reference Step 9.

For the caller's role (the human or service invoking StartSession):
> Moved to [references/diagnostic-commands.md](references/diagnostic-commands.md#step-2--caller-role-probe).
> simulate-principal-policy on the caller's role for ssm:StartSession / ssm:TerminateSession scoped to the instance and SSM-SessionManagerRunShell document ARNs.
- `ssm:StartSession` denied on the caller side → the CLI/API call
  returns `AccessDeniedException` immediately, before any session
  is attempted. **IAM_PERMISSION_MISSING (caller).**

### Step 3: VPC endpoint layer

Entry: instance `Online` (registered) but session times out;
private subnet with no internet egress.

```bash
VPC_ID=$(aws ec2 describe-instances --instance-ids <i-id> \
  --query 'Reservations[0].Instances[0].VpcId' --output text)
aws ec2 describe-vpc-endpoints --filters Name=vpc-id,Values=$VPC_ID \
  --query 'VpcEndpoints[?contains(ServiceName,`ssm`)].[ServiceName,State,VpcEndpointType]' --output table
```

Required endpoints (interface type) for private-subnet SSM:

| Endpoint service | Required for |
|---|---|
| `com.amazonaws.<region>.ssm` | Control plane: registration, StartSession API |
| `com.amazonaws.<region>.ec2messages` | Run Command / Association delivery |
| `com.amazonaws.<region>.ssmmessages` | Session data channel (the actual terminal stream) |

- Missing `ssmmessages` → session times out within seconds. The
  most common SSM session failure. **VPC_ENDPOINT_MISSING.**
- Missing `ssm` → instance never registers (cross-reference Step 1).
- Endpoint present but `State: Pending` / `Failed` → the endpoint
  is not yet usable; wait for `Available`.

Also check the endpoint security group: the VPC endpoint's SG
must allow 443 inbound from the instance's subnet/eni. A VPC
endpoint with no inbound rule on 443 is unreachable from the
instance.

### Step 4: Session connection timeout layer

Entry: session starts, then times out; VPC endpoints all present
and IAM passes.

1. **Security group egress on the instance.**
   ```bash
   aws ec2 describe-security-groups --group-ids <sg-id> \
     --query 'SecurityGroups[0].IpPermissionsEgress' --output json
   ```
   - No egress on 443 to the VPC endpoint CIDRs or the service
     ranges → the agent cannot reach `ssmmessages.*.amazonaws.com`.
     **SESSION_CONNECTION_TIMEOUT.**

2. **DNS resolution for the endpoint.**
   - Interface VPC endpoints use private DNS by default. If private
     DNS is disabled, the instance resolves `ssmmessages.*` to the
     public IP and the session fails in a no-egress VPC.
   - Check `describe-vpc-endpoints` for `PrivateDnsEnabled: true`.

3. **Instance-side agent log.**
   ```bash
   tail -n 200 /var/log/amazon/ssm/amazon-ssm-agent.log | grep -iE "session|ssmmessages|timeout"
   ```
   - `dial tcp: i/o timeout` reaching `ssmmessages.*` → network
     path broken. **SESSION_CONNECTION_TIMEOUT.**
   - `403 Forbidden` on `ssmmessages:OpenDataChannel` → IAM (Step 2).

### Step 5: Agent version layer

Entry: port forwarding or session feature returns `NotSupported`;
macOS instance cannot start sessions.

```bash
aws ssm describe-instance-information \
  --filters Key=InstanceIds,Values=<i-id> \
  --query 'InstanceInformationList[].AgentVersion' --output text
```

| Agent version | Session Manager | Port forwarding | macOS session |
|---|---|---|---|
| < 2.3.68.0 | Not supported | Not supported | Not supported |
| 2.3.68.0 – 2.3.x | Supported | Not supported | Not supported |
| 3.0.196+ | Supported | Supported | Not supported |
| 3.1.x+ | Supported | Supported | Supported |

- Below 2.3.68 → sessions fail with `NotSupported` or silently.
  **AGENT_OUTDATED.**
- Below 3.0.196 → port forwarding returns `NotSupported`.
  **AGENT_OUTDATED (port forwarding).**
- macOS below 3.1 → session API errors. **AGENT_OUTDATED (macOS).**

Agent self-update requires reaching `s3.*.amazonaws.com` or an S3
VPC endpoint. A locked-down private subnet without an S3 endpoint
stays on the old agent.

### Step 6: Session document layer

Entry: `InvalidDocument`, `InvalidDocumentVersion`, or document
schema errors on session start.

```bash
aws ssm get-document --name <document-name> --output json | jq '.'
aws ssm describe-document --name <document-name> --output json | jq '.'
```

- Document `Status: Failed` or `SchemaVersion` not `1.0` for a
  session document → document error. **SESSION_DOCUMENT_ERROR.**
- The default document `SSM-SessionManagerRunShell` should have
  `DocumentType: Session`. If `DocumentType` is `Command` or the
  schema is wrong, sessions fail. **SSM_DOCUMENT_ERROR.**
- For a custom document, the schema must match the session document
  schema (inputs for `s3BucketName`, `cloudWatchLogGroupName`,
  `kmsKeyId`, `shellProfile`). Missing fields default to no output.
- Document sharing: a session document must be shared with the
  caller account if cross-account. Missing share →
  `AccessDeniedException` on StartSession.

### Step 7: Port forwarding layer

Entry: port forwarding command connects but the forwarded port
cannot reach the target.

> Moved to [references/diagnostic-commands.md](references/diagnostic-commands.md#step-7--port-forwarding-probe).
> start-session --document-name AWS-StartPortForwardingSession with portNumber/hostName parameters.

1. **Document name.** The default port-forwarding document is
   `AWS-StartPortForwardingSession` (managed). A custom document
   must be `Session` type and use the port-forwarding schema.
2. **Target host reachability.** The `hostName` is resolved from
   the INSTANCE, not the caller. If the instance cannot route to
   `hostName` (different VPC, SG block), the forwarded port
   connects to nothing. **PORT_FORWARDING_FAILURE.**
3. **Agent version.** Port forwarding requires agent >= 3.0.196.
   Below → `NotSupported`. **AGENT_OUTDATED.**

### Step 8: Shell profile layer

Entry: session opens and closes immediately; agent log shows
`SessionTypeHandler` errors.

```bash
# On the instance, tail the agent log
tail -n 200 /var/log/amazon/ssm/amazon-ssm-agent.log | grep -iE "SessionTypeHandler|shell|profile"
```

- `.bashrc` with an `exit` / `logout` → session closes immediately.
  **SHELL_PROFILE_ERROR.**
- `.bash_profile` syntax error → session fails to spawn the shell.
  **SHELL_PROFILE_ERROR.**
- Custom `shellProfile` in the session document pointing to a
  non-existent binary → session opens, exits.
  **SHELL_PROFILE_ERROR.**

### Step 9: Audit log / session output to S3 layer

Entry: sessions work but no JSON output in the S3 session bucket.

> Moved to [references/diagnostic-commands.md](references/diagnostic-commands.md#step-9--audit-log--s3-output-probe).
> get-document s3BucketName/s3KeyPrefix, get-bucket-policy, head-bucket on the session-output bucket.

- Document `s3BucketName` empty → no S3 output configured. Add the
  bucket name in the document. **AUDIT_LOG_S3_MISSING.**
- Bucket policy missing the grant for
  `arn:aws:iam::<account>:role/<instance-role>` `s3:PutObject` on
  `arn:aws:s3:::<bucket>/<prefix>/*` → the agent writes but S3
  rejects. **AUDIT_LOG_S3_MISSING.**
- Bucket Region vs document Region mismatch → the agent writes to
  the wrong Region endpoint.
- SSE-KMS bucket where the role lacks `kms:GenerateDataKey` → write
  fails. **SESSION_RECORDING_S3.**

For session recording (shell scrollback), the same bucket and a
longer `s3KeyPrefix` apply. If scrollback is truncated, check the
document's `cloudWatchLogGroupName` (separate stream) and the
recording-enabled flag.

### Step 10: CloudWatch Logs delivery layer

Entry: sessions work but the CloudWatch Logs group is empty.

> Moved to [references/diagnostic-commands.md](references/diagnostic-commands.md#step-10--cloudwatch-logs-delivery-probe).
> get-document cloudWatchLogGroupName/cloudWatchStreamingEnabled, describe-log-groups, role logs:CreateLogStream/PutLogEvents simulation.

- Document `cloudWatchLogGroupName` empty → no CW Logs output
  configured. **CLOUDWATCH_LOGS_MISSING.**
- Role missing `logs:CreateLogStream` / `logs:PutLogEvents` → agent
  cannot write. **CLOUDWATCH_LOGS_MISSING.**
- Log group in a different account without resource-policy grant
  to the SSM service → writes denied.

### Step 11: Patch baseline blocking layer

Entry: sessions fail during a maintenance window; `ScanOnly` or
`Install` association in `Running` state.

> Moved to [references/diagnostic-commands.md](references/diagnostic-commands.md#step-11--patch-baseline-association-probe).
> describe-instance-associations-status and describe-association to detect a Running ScanOnly/Install association during the session failure window.

- Association `Status: Running` during a patch window → agent busy;
  session data channel may be slow to open. Rare; usually resolves
  when the patch completes. **PATCH_BASELINE_BLOCKING.**
- If the association is `Failed`, the patch itself errored; sessions
  are unaffected. Different root cause.

### Step 12: INSUFFICIENT_DATA — when none of the layers confirm

If every probe passes and no failing probe matches the symptom,
emit INSUFFICIENT_DATA. List the passing probes in EVIDENCE.
Recommend escalation to AWS Support with the instance id, session
id, and the failing probe outputs.

## Output specification — diagnostic block

```text
TARGET: <instance-id with session/document context>
VERDICT: ROOT_CAUSE_IDENTIFIED | INSUFFICIENT_DATA
REASON: <1-3 sentences naming the failed layer and the failing probe>
LAYER: <INSTANCE_NOT_REGISTERED | SESSION_CONNECTION_TIMEOUT |
        AGENT_OUTDATED | IAM_PERMISSION_MISSING |
        VPC_ENDPOINT_MISSING | SESSION_DOCUMENT_ERROR |
        PORT_FORWARDING_FAILURE | SHELL_PROFILE_ERROR |
        AUDIT_LOG_S3_MISSING | SESSION_RECORDING_S3 |
        CLOUDWATCH_LOGS_MISSING | PATCH_BASELINE_BLOCKING |
        SSM_DOCUMENT_ERROR | UNKNOWN>
EVIDENCE:
  - <observed symptom — error string or behaviour>
  - <failing probe — command and its output that confirms the cause>
  - <passing probes — layers ruled out>
REMEDIATION:
  1. <specific action with CLI command or API call>
  2. <verification command after the fix>
```

Field rules:

- `TARGET` includes the instance id and, when applicable, the
  session document name and session id.
- `VERDICT` is one of the two enumerated values.
- `EVIDENCE` always includes (a) symptom, (b) failing probe output,
  (c) at least one passing probe ruling out a competing layer.

## Pre-flight safety checks (run before any state-changing CLI)

- **MANDATORY CONFIRMATION GATE.** Before any state-changing
  operation (`start-session`, `terminate-session`, `put-document`,
  `update-document`, `create-vpc-endpoint`, `attach-role-policy`,
  `put-bucket-policy`), emit and await operator approval.
- **Read-only first.** Every probe in the diagnostic tree is
  read-only. Do not perform state-changing operations as probes.
- **`terminate-session`** closes a live session the operator may be
  using. Confirm before terminating; check `describe-sessions
  --state Active` first.
- **`update-document` on SSM-SessionManagerRunShell** affects every
  session using the default document. Use a custom document for
  testing changes before applying to the default.
- **`create-vpc-endpoint`** is billed hourly; confirm the endpoint
  is needed before creating. The three SSM endpoints (~$0.01/hour
  each in us-east-1) are cheap but accrue.
- **Role policy changes** affect every instance using that role.
  Use a test role on a test instance before applying to production.

## Remediation guidance

> Moved to [references/error-handling.md](references/error-handling.md#remediation-guidance).
> Per-layer fix CLIs: associate-iam-instance-profile + Core policy + agent start (INSTANCE_NOT_REGISTERED), ssmmessages inline policy (IAM), create-vpc-endpoint ssmmessages, SG egress + private DNS (TIMEOUT), agent update commands per OS, document reset (DOCUMENT), port-forwarding checks, shell profile fixes, S3 bucket policy + kms:GenerateDataKey, CloudWatch Logs config, patch-window reschedule.

## Deep reference

### Symptom → layer decision matrix

> Moved to [references/advanced-patterns.md](references/advanced-patterns.md#symptom--layer-decision-matrix).
> 12-row error-string/behaviour -> LAYER decision matrix (instance absent, ConnectionLost, ChannelClosedException, AccessDeniedException caller vs agent log, NotSupported, InvalidDocument, instant close, empty bucket/logs, macOS).

### Session document schema (SSM-SessionManagerRunShell)

> Moved to [references/session-output-and-document-reference.md](references/session-output-and-document-reference.md#session-document-schema-ssm-sessionmanagerrunshell).
> Full JSON schema of the default session document: s3BucketName/s3KeyPrefix/s3EncryptionEnabled, cloudWatchLogGroupName/cloudWatchStreamingEnabled, kmsKeyId, runAs*, shellProfile; empty output fields disable audit paths.

## Recent AWS features (2024-2026)

> Moved to [references/advanced-patterns.md](references/advanced-patterns.md#recent-aws-features-2024-2026).
> CloudWatch streaming semantics, AWS-StartPortForwardingSessionToRemoteHost, macOS 3.1.x session support, scrollback recording, VPC endpoint resource policies.

## References (load on demand)

- [advanced-patterns](references/advanced-patterns.md) — Mindset, Philosophy (control vs data plane), quick-start coverage rules, Step 0 non-obvious behaviours, symptom-to-layer decision matrix, Recent AWS features
- [diagnostic-commands](references/diagnostic-commands.md) — pre-flight probes, the Step 2 caller-role probe, and the Step 7/9/10/11 per-layer probe commands moved from SKILL.md
- [error-handling](references/error-handling.md) — per-layer remediation fix commands moved from SKILL.md
- [session-output-and-document-reference](references/session-output-and-document-reference.md) — session document schema, audit-log bucket policies, CloudWatch Logs delivery, shell profiles, port-forwarding document variants
- [vpc-endpoint-and-iam-reference](references/vpc-endpoint-and-iam-reference.md) — three-endpoint matrix, instance-role and caller-role permission maps, agent version support matrix

## Domain

AWS CloudOps / Systems Manager Session Manager, Instance
Registration Diagnostics, VPC Endpoint Configuration, IAM Role
Permissions, Session Output and Audit Log Delivery, Port
Forwarding, and Shell Profile Management.

## AWS documentation

- **AWS Systems Manager Session Manager** — https://docs.aws.amazon.com/systems-manager/latest/userguide/session-manager.html
- **Setting up Session Manager** — https://docs.aws.amazon.com/systems-manager/latest/userguide/session-manager-getting-started.html
- **Working with Session Manager** — https://docs.aws.amazon.com/systems-manager/latest/userguide/session-manager-working-with-sessions.html
- **Troubleshooting Session Manager** — https://docs.aws.amazon.com/systems-manager/latest/userguide/session-manager-troubleshooting.html
- **VPC endpoints for Systems Manager** — https://docs.aws.amazon.com/systems-manager/latest/userguide/setup-create-vpc.html
- **AmazonSSMManagedInstanceCore policy** — https://docs.aws.amazon.com/aws-managed-policy/latest/reference/AmazonSSMManagedInstanceCore.html
- **SSM Agent version history** — https://docs.aws.amazon.com/systems-manager/latest/userguide/ssm-agent.html
- **Session Manager auditing** — https://docs.aws.amazon.com/systems-manager/latest/userguide/session-manager-auditing.html
- **Port forwarding with Session Manager** — https://docs.aws.amazon.com/systems-manager/latest/userguide/session-manager-working-with-sessions-port-forwarding.html
- **AWS Health** — https://docs.aws.amazon.com/health/latest/ug/
