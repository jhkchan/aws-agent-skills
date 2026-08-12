---
name: ssm-session-troubleshooter
description: >-
  Diagnoses AWS Systems Manager Session Manager failures through a
  thirteen-category diagnostic tree: managed instance not showing
  up (SSM Agent not running, activation code expired, hybrid
  enrollment), session connection timeout (ssmmessages endpoint,
  Security group egress), SSM Agent version outdated (session
  features require minimum agent version), IAM role missing
  ssm:StartSession / ssm:TerminateSession / ssm:ResumeSession
  (AmazonSSMManagedInstanceCore), VPC endpoint for SSM missing one
  of the three required endpoints (ssm, ec2messages, ssmmessages),
  session document errors (SSM_Session document schema or sharing),
  port forwarding failures (local-port-forwarding document and
  target-host reachability), shell profile errors
  (SSM-SessionManagerRunShell profile misconfig), audit log
  delivery to S3 missing (S3 bucket policy for session-output),
  session recording to S3 (encryption and bucket Region),
  CloudWatch Logs delivery missing (log group permission on the
  instance role), macOS vs Linux agent differences (session
  support matrix), patch baseline association blocking session
  (ScanOnly / InstallOverrideList maintenance window in flight),
  and Systems Manager document (SSM Document) errors. Walks
  symptoms to a verified root cause with evidence-backed probes;
  emits ROOT_CAUSE_IDENTIFIED or INSUFFICIENT_DATA.
version: 0.1.0
author: Jacky Chan — AWS Community Builder
license: Apache-2.0
compatibility: Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). Offline symptom classification works from pasted error messages and instance configuration. Live-account diagnosis uses aws ssm describe-instance-information, describe-sessions, get-document, describe-instance-properties, aws ec2 describe-instances / describe-vpc-endpoints / describe-security-groups, aws iam simulate-principal-policy on the instance role, aws logs describe-log-groups / filter-log-events, aws s3api get-bucket-policy on the session-output bucket, and aws ssm describe-association / describe-instance-associations-status (AWS CLI v2, SSO or key-based credentials).
keywords:
- SSM
- Session Manager
- ssm:StartSession
- SSM Agent
- AmazonSSMManagedInstanceCore
- VPC endpoint
- ssmmessages
- ec2messages
- port forwarding
- shell profile
- session recording
- S3 audit logs
- CloudWatch Logs
- hybrid enrollment
- activation code
- patch baseline
- SSM Document
- troubleshooting
tags:
- ssm
- management
- troubleshooting
- session-manager
- vpc-endpoint
- iam-role
- port-forwarding
- session-recording
- audit-logs
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: true
  phase: 2
  supports_pipeline: true
  entry_point: false
  family: Management
  task_type: troubleshoot
  skill_class: capability
  lifecycle_status: active
  verdict_shape: ROOT_CAUSE_IDENTIFIED | INSUFFICIENT_DATA
  when_to_use: Diagnosing an SSM Session Manager failure (managed instance not showing in the console, session connection timeout, port forwarding failure, "is not registered to the account or role" error, missing audit logs in S3, missing CloudWatch Logs, session recording failure, shell profile error, patch-baseline-blocked session, SSM Document error, agent version too old for session features), walking a symptom to the failed layer with verify and fix commands, validating why a session cannot start or connect, or triaging a "Session Manager is broken" page where the root cause may be agent, IAM role, VPC endpoint, document, shell profile, or audit-log config — not necessarily the SSM service itself.
  when_not_to_use: SSM Run Command / Automation execution debugging (use ssm-automation-deployer or a run-command skill), EC2 instance reachability at the OS level (use ec2-instance-reachability checks), patch compliance posture audits (use ssm-patch-compliance-automator), or IAM policy authoring for the instance role (use iam-least-privilege-advisor). This skill diagnoses Session Manager connectivity and session-output failures; it does not audit patch baseline posture or debug Run Command document execution.
  activation_triggers:
  - SSM Session Manager connection failed
  - SSM session timeout
  - managed instance not showing up
  - instance not registered SSM
  - SSM Agent not running
  - ssm:StartSession denied
  - SSM port forwarding failed
  - channel closed Session Manager
  - ssmmessages endpoint
  - VPC endpoint SSM missing
  - SSM session recording S3
  - SSM audit logs missing
  - SessionManagerRunShell
  - SSM Document error
  - SSM agent version outdated
  - hybrid activation expired
  - patch baseline blocking session
  - troubleshoot SSM Session Manager
  invocation_schema: 'Input: either (a) a symptom description (error message, observed behaviour, "session times out after 10s", "instance not in the console"), optionally paired with the instance configuration (describe-instance-information output) and recent SSM / CloudWatch logs, OR (b) an InstanceId plus session context (document name, session id, target host for port forwarding, VPC endpoint config) for live-account diagnosis. Output: a deterministic TARGET/VERDICT/REASON/LAYER/EVIDENCE/REMEDIATION block where VERDICT ∈ {ROOT_CAUSE_IDENTIFIED, INSUFFICIENT_DATA} and LAYER ∈ {INSTANCE_NOT_REGISTERED, SESSION_CONNECTION_TIMEOUT, AGENT_OUTDATED, IAM_PERMISSION_MISSING, VPC_ENDPOINT_MISSING, SESSION_DOCUMENT_ERROR, PORT_FORWARDING_FAILURE, SHELL_PROFILE_ERROR, AUDIT_LOG_S3_MISSING, SESSION_RECORDING_S3, CLOUDWATCH_LOGS_MISSING, PATCH_BASELINE_BLOCKING, SSM_DOCUMENT_ERROR, UNKNOWN}.'
  invocation_example: "# Minimal valid input (offline symptom classification):\nSymptom: \"EC2 instance i-0abcdef1234567890 in a private subnet does\nnot appear in the SSM Fleet Manager console. The instance\nhas the AmazonSSMManagedInstanceCore role attached but is\nin a VPC with no ssmmessages VPC endpoint. Sessions started\nfrom other instances in a public subnet work fine.\"\nInstanceId: i-0abcdef1234567890\nVPC: vpc-priv (no internet gateway, no NAT gateway)\nInstanceRole: EC2-SSM-Role (AmazonSSMManagedInstanceCore attached)\nVPC endpoints configured: ssm (interface), ec2messages (interface)\nVPC endpoints MISSING: ssmmessages\nLast log line: \"Session Manager connection timed out\""
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
- **Always verify with a probe, never guess.** Each layer has a
  single command that proves or disproves it. A
  `ROOT_CAUSE_IDENTIFIED` verdict requires positive evidence — a
  failing probe that matches the symptom.
- **Private subnet SSM requires three VPC endpoints.** Session
  Manager in a no-internet VPC needs `ssm`, `ec2messages`, AND
  `ssmmessages` interface endpoints. Missing any one produces
  different symptoms: missing `ssm` blocks registration, missing
  `ec2messages` blocks command delivery, missing `ssmmessages`
  blocks session data channel (the session times out). Operators
  who "added the SSM endpoint" but still see timeouts usually miss
  `ssmmessages`.
- **The instance role needs AmazonSSMManagedInstanceCore.** This
  managed policy grants `ssm:StartSession` via the Session Manager
  document, plus `ssmmessages:CreateControlChannel`,
  `ssmmessages:CreateDataChannel`, and `ssmmessages:OpenControlChannel`,
  `ssmmessages:OpenDataChannel`. Without these, the agent cannot
  open the session data plane even if StartSession succeeds.
- **SSM Agent version gates session features.** Session Manager
  requires agent 2.3.68.0 or higher; port forwarding requires
  3.0.196 or higher; macOS session support requires 3.1.x. An
  agent below the threshold either fails silently or returns a
  `NotSupported` error. Always read `describe-instance-information
  --query 'InstanceInformationList[].AgentVersion'` before
  debugging session features.

## Mindset

A failing Session Manager connection is usually an agent, IAM,
network, or configuration incident wearing a service costume. The
SSM service is healthy in the majority of cases; the broken thing
is the SSM Agent on the instance, the instance role missing a
permission, one of the three required VPC endpoints, the session
document, the shell profile, or the audit-log bucket policy. Treat
the SSM service as innocent until the agent, IAM, network, and
document layers are proven clean. Senior cloud engineers do not
start by restarting the instance; they start with
`describe-instance-information`, `describe-vpc-endpoints`, and
`simulate-principal-policy` on the instance role.

## Philosophy

- **Session Manager has two planes: control and data.** The control
  plane (SSM API: StartSession, TerminateSession) runs over the
  `ssm` endpoint. The data plane (the actual terminal stream) runs
  over the `ssmmessages` endpoint. The `ec2messages` endpoint
  carries Run Command and Association traffic. An instance with
  only the `ssm` endpoint registers and receives commands but
  cannot open a session data channel — sessions start and
  immediately time out. Operators who "added the SSM endpoint" but
  still see session timeouts usually miss `ssmmessages`.
- **Registration ≠ Session-ready.** An instance that appears in
  `describe-instance-information` with `PingStatus: Online` has a
  working control channel. That does NOT mean Session Manager works
  — the data channel (`ssmmessages`) is a separate path. Operators
  who say "the instance is Online but sessions fail" need to check
  `ssmmessages:OpenDataChannel` on the role and the `ssmmessages`
  VPC endpoint.
- **The instance role gates both StartSession AND the data channel.**
  `ssm:StartSession` lets the API call succeed; the actual session
  requires `ssmmessages:CreateControlChannel`,
  `ssmmessages:CreateDataChannel`, `ssmmessages:OpenControlChannel`,
  and `ssmmessages:OpenDataChannel` on the instance role.
  AmazonSSMManagedInstanceCore includes all of these. A custom role
  missing the `ssmmessages:*` permissions starts the session on the
  client side but the agent cannot open the data channel — the
  session times out within seconds.
- **Session output (audit logs, recording) is configured at the
  document level, not the instance level.** The `SSM-SessionManagerRunShell`
  document (or a custom session document) carries the S3 bucket
  name, CloudWatch Logs log group, KMS key, and shell profile. An
  instance that starts sessions fine but produces no audit logs has
  a document-side configuration gap or a bucket-policy gap, not an
  instance-side problem.

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

```bash
# 1. Instance information (AgentVersion, PingStatus, PlatformName,
#    RegistrationDate, LastPingDateTime, AssociationStatus, IamRole)
aws ssm describe-instance-information --output json

aws ssm describe-instance-properties --instance-id <i-id> --output json

# 2. Recent sessions (Status, Output, StartDate, EndDate)
aws ssm describe-sessions --state History \
  --instance-id <i-id> --output json

# 3. Session document (the SSM-SessionManagerRunShell default or custom)
aws ssm get-document --name SSM-SessionManagerRunShell --output json

# 4. Instance role — simulate the session permissions
aws ec2 describe-instances --instance-ids <i-id> \
  --query 'Reservations[0].Instances[0].IamInstanceProfile.Arn' --output text

aws iam simulate-principal-policy \
  --policy-source-arn "<instance-role-arn>" \
  --action-names ssm:StartSession ssm:UpdateInstanceInformation \
    ssmmessages:CreateControlChannel ssmmessages:CreateDataChannel \
    ssmmessages:OpenControlChannel ssmmessages:OpenDataChannel \
    s3:PutObject logs:CreateLogStream \
  --output json

# 5. VPC endpoints for the instance's VPC (ssm, ec2messages, ssmmessages)
VPC_ID=$(aws ec2 describe-instances --instance-ids <i-id> \
  --query 'Reservations[0].Instances[0].VpcId' --output text)
aws ec2 describe-vpc-endpoints --filters Name=vpc-id,Values=$VPC_ID \
  --query 'VpcEndpoints[].ServiceName' --output json

# 6. Security group egress (must allow 443 to the endpoints or service)
SG_ID=$(aws ec2 describe-instances --instance-ids <i-id> \
  --query 'Reservations[0].Instances[0].SecurityGroups[0].GroupId' --output text)
aws ec2 describe-security-groups --group-ids $SG_ID --output json

# 7. SSM agent log (CloudWatch Logs if configured, or fetch via SSM Run Command)
aws logs filter-log-events \
  --log-group-name /aws/ssm/<i-id>/amazon-ssm-agent \
  --start-time $(date -d '-30 minutes' +%s)000 \
  --filter-pattern '"SessionManager" OR "ssmmessages" OR "AccessDenied"' \
  --output json

# 8. AWS Health (regional SSM events, scheduled maintenance)
aws health describe-events --filter eventStatusCodes=OPEN,UPCOMING \
  --region us-east-1 --output json
```

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

- **Three VPC endpoints, not one.** Private-subnet SSM needs `ssm`,
  `ec2messages`, AND `ssmmessages` interface endpoints. Missing
  `ssm` blocks registration; missing `ec2messages` blocks Run
  Command; missing `ssmmessages` blocks the session data channel.
  Operators who "added the SSM VPC endpoint" usually added only
  `ssm` and are surprised sessions still time out.
- **`ssm:StartSession` is on the CALLER, not the instance.** The
  human or service invoking StartSession needs `ssm:StartSession`
  on the document and instance. The INSTANCE needs the
  `ssmmessages:*` permissions to open the data channel. These are
  separate roles and separate permissions; granting the caller
  `ssm:StartSession` does not help if the instance role lacks
  `ssmmessages:OpenDataChannel`.
- **AmazonSSMManagedInstanceCore includes the ssmmessages actions.**
  The older `AmazonEC2RoleforSSM` policy is deprecated and DOES
  NOT include all `ssmmessages:*` actions. Instances still on the
  old policy appear Online but fail to open sessions. Always
  verify the managed policy name in the role.
- **Session Manager requires agent 2.3.68.0 or higher.** Below
  that, the agent does not register the session handler. Port
  forwarding requires 3.0.196; macOS sessions require 3.1.x. The
  agent self-updates if it can reach `s3.*.amazonaws.com` (or the
  S3 VPC endpoint), but a locked-down instance with no S3 endpoint
  stays on the old agent indefinitely.
- **The session document carries the audit configuration.** The
  default document `SSM-SessionManagerRunShell` carries
  `s3BucketName`, `cloudWatchLogGroupName`, `kmsKeyId`, and the
  `shellProfile`. A custom document can override these. If sessions
  work but produce no audit logs, the document is the place to
  look, not the instance.
- **Shell profile errors close the session immediately.** A bad
  shell profile (syntax error in a sourced file, a `logout` /
  `exit` in `.bashrc`, or a prompt that does not terminate) causes
  the session to open and close within milliseconds. The agent log
  shows `SessionTypeHandler` errors. Operators who "see the session
  flash and disappear" should check the shell profile, not the
  network.
- **Hybrid activations expire.** A non-EC2 instance (on-premises,
  other-cloud) registered via `create-activation` has an
  activation code that is single-use and an expiration date. After
  expiration, the instance cannot re-register if the agent is
  restarted. The instance disappears from `describe-instance-information`.
- **Patch baseline associations do not block sessions directly,
  but a patch in `Running` state can hold the agent busy.** If the
  association is `Install` and a large patch window is in flight,
  the agent may be slow to respond to the session data channel
  open. This is rare; check `describe-instance-associations-status`
  if sessions fail during a known maintenance window.
- **macOS and Linux agents differ.** macOS session support arrived
  in agent 3.1.x; earlier macOS agents register for Run Command
  but cannot open Session Manager sessions. Linux has the broadest
  support; Windows requires the agent installed via EC2Launch v2
  or the Amazon-provided AMI.
- **`describe-sessions --state Active` shows sessions the SSM
  service thinks are still open.** A session that timed out on the
  client but was never terminated by the agent stays in `Active`
  state until the service-side timeout (default 20 minutes).
  Operators who "see 50 open sessions" but only one is real should
  call `terminate-session` on stale sessions.

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
```bash
aws iam simulate-principal-policy \
  --policy-source-arn "<caller-role-arn>" \
  --action-names ssm:StartSession ssm:TerminateSession \
  --resource-arns "arn:aws:ssm:<region>:<account>:instance/<i-id>" \
    "arn:aws:ssm:<region>:<account>:document/SSM-SessionManagerRunShell" \
  --output json
```
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

```bash
aws ssm start-session \
  --document-name AWS-StartPortForwardingSession \
  --target <i-id> \
  --parameters '{"portNumber":["22"], "hostName":["10.0.1.50"]}'
```

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

```bash
aws ssm get-document --name SSM-SessionManagerRunShell --output json | \
  jq '.DocumentContent.inputs.s3BucketName, .DocumentContent.inputs.s3KeyPrefix'
aws s3api get-bucket-policy --bucket <session-output-bucket> --output json | jq '.'
aws s3api head-bucket --bucket <session-output-bucket>
```

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

```bash
aws ssm get-document --name SSM-SessionManagerRunShell --output json | \
  jq '.DocumentContent.inputs.cloudWatchLogGroupName, .DocumentContent.inputs.cloudWatchStreamingEnabled'
aws logs describe-log-groups --log-group-name-prefix <prefix> --output json
aws iam simulate-principal-policy --policy-source-arn "<role-arn>" \
  --action-names logs:CreateLogStream logs:PutLogEvents --output json
```

- Document `cloudWatchLogGroupName` empty → no CW Logs output
  configured. **CLOUDWATCH_LOGS_MISSING.**
- Role missing `logs:CreateLogStream` / `logs:PutLogEvents` → agent
  cannot write. **CLOUDWATCH_LOGS_MISSING.**
- Log group in a different account without resource-policy grant
  to the SSM service → writes denied.

### Step 11: Patch baseline blocking layer

Entry: sessions fail during a maintenance window; `ScanOnly` or
`Install` association in `Running` state.

```bash
aws ssm describe-instance-associations-status --instance-id <i-id> --output json
aws ssm describe-association --association-id <assoc-id> --output json
```

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

### For INSTANCE_NOT_REGISTERED — agent or role missing

```bash
# Attach the instance profile if missing
aws ec2 associate-iam-instance-profile \
  --instance-id <i-id> --iam-instance-profile Name=<profile-name>

# Ensure the role has AmazonSSMManagedInstanceCore
aws iam attach-role-policy --role-name <role-name> \
  --policy-arn arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore

# Start the agent on the instance (Linux)
sudo systemctl enable --now amazon-ssm-agent
```

### For IAM_PERMISSION_MISSING — role or caller missing ssm actions

Add the missing actions to the instance role (use
AmazonSSMManagedInstanceCore if the role is on the deprecated
policy) or to the caller's policy.

```bash
aws iam put-role-policy --role-name <role-name> \
  --policy-name SsmSessionAccess \
  --policy-document '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Action": ["ssmmessages:CreateControlChannel",
                  "ssmmessages:CreateDataChannel",
                  "ssmmessages:OpenControlChannel",
                  "ssmmessages:OpenDataChannel"],
      "Resource": "*"
    }]
  }'
```

Verify with `simulate-principal-policy`.

### For VPC_ENDPOINT_MISSING — add the missing endpoint

```bash
aws ec2 create-vpc-endpoint --vpc-id <vpc-id> \
  --service-name com.amazonaws.<region>.ssmmessages \
  --subnet-ids <private-subnet-id> \
  --security-group-ids <sg-id> \
  --vpc-endpoint-type Interface --output json
```

Repeat for `ssm` and `ec2messages` if those are also missing.
Ensure the endpoint's security group allows 443 inbound from the
instance's subnet.

### For SESSION_CONNECTION_TIMEOUT — network path

Add the SG egress rule for 443 to the VPC endpoint CIDRs or service
ranges. Enable private DNS on the VPC endpoint if disabled.

### For AGENT_OUTDATED — update the agent

On the instance, force an update or install the latest agent:

```bash
sudo yum update -y amazon-ssm-agent    # Amazon Linux 2 / 2023
sudo snap refresh amazon-ssm-agent     # Ubuntu 16.04+
brew upgrade amazon-ssm-agent          # macOS
```

For a private subnet without internet, add an S3 VPC endpoint so
the agent can self-update from the S3 package bucket.

### For SESSION_DOCUMENT_ERROR / SSM_DOCUMENT_ERROR

```bash
# Reset the default document
aws ssm update-document --name SSM-SessionManagerRunShell \
  --content file://default-session-document.json

# Or create a custom document
aws ssm create-document --name Custom-Session \
  --document-type Session \
  --content file://custom-session-document.json
```

### For PORT_FORWARDING_FAILURE

1. Verify the target host is reachable from the instance (not the
   caller): `ssh <i-id> ping <target-host>`.
2. Update the agent to >= 3.0.196.
3. Use `AWS-StartPortForwardingSessionToRemoteHost` for remote-host
   forwarding (different from local forwarding to the instance
   itself).

### For SHELL_PROFILE_ERROR

1. Inspect the shell profile on the instance:
   `cat ~/.bashrc ~/.bash_profile` (or the configured `shellProfile`).
2. Remove any `exit` / `logout` / syntax errors.
3. Update the document `shellProfile` to a tested script.

### For AUDIT_LOG_S3_MISSING / SESSION_RECORDING_S3

1. Set `s3BucketName` in the session document.
2. Update the bucket policy to grant the instance role `s3:PutObject`:
   ```bash
   aws s3api put-bucket-policy --bucket <session-bucket> --policy '{
     "Version": "2012-10-17",
     "Statement": [{
       "Effect": "Allow",
       "Principal": {"AWS": "arn:aws:iam::<account>:role/<instance-role>"},
       "Action": "s3:PutObject",
       "Resource": "arn:aws:s3:::<session-bucket>/*"
     }]
   }'
   ```
3. For SSE-KMS buckets, add `kms:GenerateDataKey` to the instance
   role on the KMS key ARN.

### For CLOUDWATCH_LOGS_MISSING

1. Set `cloudWatchLogGroupName` and `cloudWatchStreamingEnabled: true`
   in the document.
2. Add `logs:CreateLogStream`, `logs:PutLogEvents` to the instance
   role on the log group ARN.
3. For cross-account log groups, add a resource policy on the
   destination account granting `logs:PutLogEvents` to the SSM
   service or the source-account role.

### For PATCH_BASELINE_BLOCKING

Wait for the patch association to complete, or reschedule the
maintenance window outside session hours.

## Deep reference

### Symptom → layer decision matrix

```
Error string / behaviour                              → Layer
instance absent from describe-instance-information    → INSTANCE_NOT_REGISTERED
PingStatus: ConnectionLost / InActive                 → INSTANCE_NOT_REGISTERED / AGENT_OUTDATED
ChannelClosedException / session times out            → SESSION_CONNECTION_TIMEOUT / VPC_ENDPOINT_MISSING
AccessDeniedException on start-session (caller)       → IAM_PERMISSION_MISSING (caller)
ssmmessages:OpenDataChannel AccessDenied (agent log)  → IAM_PERMISSION_MISSING (instance)
NotSupported for port forwarding (agent < 3.0.196)    → AGENT_OUTDATED
InvalidDocument / InvalidDocumentVersion              → SESSION_DOCUMENT_ERROR
session opens then closes immediately                 → SHELL_PROFILE_ERROR
session bucket empty                                  → AUDIT_LOG_S3_MISSING
CloudWatch Logs group empty                           → CLOUDWATCH_LOGS_MISSING
macOS session fails, agent < 3.1                      → AGENT_OUTDATED
```

### Session document schema (SSM-SessionManagerRunShell)

```json
{
  "schemaVersion": "1.0",
  "sessionType": "Standard_Stream",
  "inputs": {
    "s3BucketName": "",
    "s3KeyPrefix": "",
    "s3EncryptionEnabled": false,
    "cloudWatchLogGroupName": "",
    "cloudWatchStreamingEnabled": false,
    "kmsKeyId": "",
    "runAsEnabled": false,
    "runAsDefaultUser": "",
    "shellProfile": {"linux": "bash", "windows": "PowerShell"}
  }
}
```

Empty `s3BucketName` / `cloudWatchLogGroupName` disable those
output paths. Sessions work but produce no audit trail.

## Recent AWS features (2024-2026)

- **Session Manager streaming via CloudWatch (2024-2025):**
  `cloudWatchStreamingEnabled: true` streams session output
  near-real-time. Diagnostically, empty CloudWatch Logs with
  streaming disabled is expected; empty with streaming enabled is
  the bug.
- **Port forwarding to remote hosts (2024):**
  `AWS-StartPortForwardingSessionToRemoteHost` document allows
  forwarding to a target host OTHER than the SSM instance. The
  target host is resolved from the instance, not the caller.
- **macOS session support (2024-2025):** Requires agent 3.1.x or
  higher. Operators who installed the agent via Homebrew on
  older macOS AMIs may be on a 2.x agent that registers for Run
  Command but cannot open sessions.
- **Session recording with scrollback (2024-2025):** Shell
  scrollback can be recorded to S3 separately from the JSON audit
  log. The recording flag and `s3KeyPrefix` differ; check both.
- **VPC endpoint policies (2024):** Interface VPC endpoints now
  support a resource policy that can restrict which IAM principals
  can use the endpoint. A restrictive policy can block the instance
  role from `ssmmessages` even though the endpoint exists.

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
