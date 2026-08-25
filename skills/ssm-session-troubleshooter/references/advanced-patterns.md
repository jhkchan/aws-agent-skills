# Advanced Patterns — ssm-session-troubleshooter

> Moved verbatim from SKILL.md for progressive disclosure (agentskills.io). Load on demand.

## Quick start — verification and coverage rules

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
