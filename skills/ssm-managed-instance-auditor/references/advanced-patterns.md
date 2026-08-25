# Advanced Patterns — SSM Managed Instance Auditor

Expert-knowledge deep dives, edge cases, and SSM internals moved from SKILL.md. Load on demand.

## Step 0: Expert knowledge — non-obvious SSM behaviors (moved from SKILL.md)

These behaviours are easy to misjudge without operational SSM experience.
Each changes a verdict if ignored:

- **`describe-instance-information` only shows instances SSM already
  knows about.** A freshly launched EC2 instance with no IAM profile
  will NOT appear in this API at all. To find the true fleet coverage
  gap, diff `ec2 describe-instances` (full EC2 set) against
  `ssm describe-instance-information` (managed subset). Missing
  instances are UNMANAGED by Rule C-1 — silent coverage holes.

- **`AmazonSSMManagedInstanceCore` is the modern role policy.** Older
  accounts carry the deprecated `AmazonEC2RoleforSSM` (now
  `AmazonSSMRoleForInstancesQuickSetup`). The modern policy adds
  Session Manager, CloudWatch Logs delivery, and Inventory permissions
  that the legacy policy lacks. A "managed" instance on the legacy
  policy may show green associations but lack Session Manager
  capability — classify as CONFIG_GAP (Rule V-2), not OK.

- **`PingStatus` is heartbeat, not health.** `Active` only means the
  agent pinged SSM in the last ~5 minutes; it does NOT mean associations
  are running, patches are current, or Session Manager works. Always
  pair `PingStatus` with `LastPingDateTime` — an instance can be
  `Active` but stale (ping > 1 hour ago indicates a flapping agent).

- **The 5-minute heartbeat is a soft SLA.** The SSM Agent checks in
  approximately every 5 minutes, but transient network blips or
  `DescribeInstanceInformation` eventual-consistency can produce stale
  readings. Treat `LastPingDateTime` > 1 hour as the UNMANAGED
  threshold (Rule C-2); anything 5-60 minutes stale is a soft warning,
  not a verdict driver.

- **`ConnectionLost` vs `Inactive` is a recovery signal.** Both are
  UNMANAGED, but `ConnectionLost` (recent loss) often recovers on agent
  restart; `Inactive` (>14 days) typically means the instance is
  stopped, terminated, or the agent is uninstalled. The remediation
  differs: `ConnectionLost` → investigate network/agent;
  `Inactive` → verify the instance still exists.

- **Patch Group is a TAG, not an association.** Instances are linked to
  a patch baseline via the case-sensitive tag key `Patch Group` (with
  space, capital G). The value maps to a `PatchBaselineName` or
  baseline-defined group. Without this tag, the instance falls back to
  the default regional patch baseline — silently. A "patched" fleet
  with no `Patch Group` tags may be patching against the wrong
  baseline. Flag as CONFIG_GAP (Rule P-2).

- **`AWS-ApplyPatchBaseline` has two Operations: `Scan` and `Install`.**
  `Scan` records compliance but does not patch; `Install` applies
  patches. An association running `Operation=Scan` will keep compliance
  fresh without ever remediating — surface this in findings. The
  default Operation if unspecified is `Scan`.

- **Default baselines are REGIONAL and per-OS.** Each AWS Region has
  `AWS-RunPatchBaseline` (Linux family) and `AWS-WindowsPatchBaseline`
  pre-provisioned by AWS. Custom baselines only take effect if
  explicitly set as default OR selected via `Patch Group` tag. A custom
  baseline that is not "set as default" and has no matching tag is
  dead configuration — flag as CONFIG_GAP.

- **Association status and compliance status are separate APIs.**
  `describe-instance-associations-status` returns the last execution
  status (`Success`/`Failed`/`Pending`). `list-compliance-items`
  returns patch compliance (`COMPLIANT`/`NON_COMPLIANT`). A `Success`
  association can produce `NON_COMPLIANT` compliance (scan found
  missing patches). NEVER treat association green as patch green.

- **Session Manager requires NO inbound ports.** The `ssmmessages`
  traffic is outbound from the instance to the SSM service over
  HTTPS/443. Keeping TCP/22 open "for fallback" defeats the primary
  security benefit. A managed instance with port 22 open to any CIDR
  is NO_SESSION_MANAGER (Rule S-1), regardless of whether Session
  Manager is also configured — the open port is a parallel, weaker
  control.

- **Session logging is opt-in and three-layered.** Session Manager can
  log to (1) S3 (full transcript), (2) CloudWatch Logs (searchable),
  (3) KMS encryption (envelope). Without at least one, sessions are
  unauditable — a compliance failure for most audit frameworks.
  Default is NO logging. Flag absence as CONFIG_GAP (Rule S-3).

- **Hybrid activation `mi-*` instances use the activation role, not an
  EC2 profile.** `IamRoleARN` for `ResourceType: ManagedInstance` comes
  from the activation code/ID exchange at registration time. If that
  role lacks `AmazonSSMManagedInstanceCore`, the instance can register
  but cannot run associations or sessions. Different remediation path
  than EC2 (re-activate with a new role, not re-attach a profile).

- **`AWS-UpdateSSMAgent` is the auto-update association.** Without it,
  the agent only updates on instance stop/start or manual `SendCommand`.
  AWS does not auto-update agents on a schedule by default. Missing
  this association is the root cause of most `IsLatestVersion: false`
  findings (Rule V-1).

- **Rate limits on `SendCommand`:** SSM enforces a per-instance command
  concurrency limit (default 1 concurrent command per instance; a
  second command returns `InvalidInstanceId` or
  `TargetNotConnected`). Diagnose as a transient back-off, not a
  coverage failure.

- **VPC endpoints for private subnets:** three interface endpoints are
  required for fully-private SSM: `ssm`, `ssmmessages`, `ec2messages`.
  Missing any one produces `ConnectionLost` PingStatus even with
  correct IAM and a running agent. This is a NETWORKING failure, not
  an agent failure — remediation is "deploy endpoints", not "restart
  agent".
## Edge-case handling (moved from SKILL.md)

- **Stopped EC2 instance.** A stopped EC2 instance will not appear in
  `describe-instance-information`. Cross-reference
  `ec2 describe-instances --filters Name=instance-state-name,Values=stopped`
  — these are NOT unmanaged, they are offline. Note as informational
  ("stopped, last seen <date>"); do not emit UNMANAGED.

- **Freshly launched instance (< 5 min ago).** The SSM Agent takes 1-5
  minutes to bootstrap on first boot. Treat `LastPingDateTime` absence
  on an instance launched < 5 min ago as PENDING, not UNMANAGED.

- **`mi-*` hybrid instance with expired activation.** Hybrid activations
  have an expiration date; an expired activation blocks new instances
  from registering but does NOT disconnect already-registered ones. If
  a `mi-*` instance is `ConnectionLost`, check activation expiry via
  `aws ssm describe-activations` — different remediation than EC2.

- **Mac instances (`EC2MacHost`).** macOS hosts require a dedicated
  SSM setup (`AmazonSSMMonitoring`, `AmazonSSMMaintenance`,
  `EC2MacHost` resource type). Standard EC2 rules do not apply. Note
  and skip detailed audit if not configured for macOS.

- **Multiple patch baselines for one instance.** If an instance matches
  multiple `Patch Group` tag values, the lexicographically-first
  baseline wins (SSM does not merge). Surface as CONFIG_GAP — the
  governance intent is ambiguous.

- **Association in `Pending` state.** `Pending` is in-flight, not
  failed. Do not flag — re-evaluate after the schedule window passes.
## Deep reference: SSM internals (moved from SKILL.md)

### Required IAM permissions (per dimension)

| Dimension | API calls | Minimum IAM action |
|---|---|---|
| Coverage | `ssm:DescribeInstanceInformation`, `ec2:DescribeInstances` | `ssm:DescribeInstanceInformation`, `ec2:Describe*`, `iam:ListInstanceProfiles` |
| Associations | `ssm:DescribeInstanceAssociationsStatus`, `ssm:DescribeAssociation` | `ssm:DescribeInstanceAssociationsStatus`, `ssm:DescribeAssociation`, `ssm:ListAssociations` |
| Patch | `ssm:DescribePatchStates`, `ssm:ListComplianceItems`, `ssm:DescribePatchBaselines` | `ssm:DescribePatchStates`, `ssm:ListComplianceItems`, `ssm:DescribePatchBaselines` |
| Session | `ssm:DescribeSessions`, `ec2:DescribeSecurityGroups` | `ssm:DescribeSessions`, `ec2:DescribeSecurityGroups` |
| Inventory | `ssm:GetInventory`, `ssm:ListInventoryEntries` | `ssm:GetInventory`, `ssm:ListInventoryEntries` |
| Run Command | `ssm:ListCommands`, `ssm:GetCommandInvocation` | `ssm:ListCommands`, `ssm:GetCommandInvocation` |

### VPC endpoints (private subnet SSM)

Three interface endpoints are required for SSM in a private VPC without
internet egress:

- `com.amazonaws.<region>.ssm` — control-plane API (`describe-*`,
  `send-command`, `start-session`).
- `com.amazonaws.<region>.ssmmessages` — Session Manager data channel
  (the WebSocket-style message stream for `start-session`).
- `com.amazonaws.<region>.ec2messages` — agent-to-SSM polling
  (`DescribeInstanceInformation` ping, command dispatch).

Without all three, the agent may show `Active` briefly but will degrade
to `ConnectionLost` within ~30 minutes as the polling channel fails.
The endpoint security group must allow HTTPS/443 inbound from the
instance subnet.

### Hybrid activation lifecycle

- `create-activation` returns an `ActivationCode` + `ActivationId`.
  The code is single-use-per-registration and expires at `ExpiryDate`.
- On the on-prem host, `amazon-ssm-agent -register -code <code> -id <id> -region <region>`
  exchanges the code for the activation's IAM role ARN. The instance
  becomes `mi-<uuid>`.
- The IAM role is fixed at registration; rotating it requires
  re-registration with a new activation. There is no
  `replace-iam-role` API for hybrid instances.
- `ActivationCode` is a credential — if leaked, anyone can register
  instances under your account until `RegistrationLimit` is reached or
  `ExpiryDate` passes. Audit `describe-activations` for stale codes.

### Patch baseline mechanics

- Approval rules are JSON on the baseline (`ApprovalRules.PatchRules[]`):
  each rule has `PatchFilterGroup` (CVE/classification), `ApproveAfterDays`
  (auto-approve N days after release), and `ComplianceLevel`
  (CRITICAL/HIGH/MEDIUM/LOW).
- `ApproveAfterDays: 0` means "approve immediately on release" —
  aggressive. `7` is the common safe default for security patches.
- A baseline must be either (a) set as the default for its OS/region
  (`set-default-patch-baseline`), or (b) selected via `Patch Group`
  tag value matching the baseline's name. Both paths are valid; the
  default wins if no tag matches.
- Patch Manager does NOT auto-reboot. Windows patches that require
  reboot show `InstalledPending` until the next reboot. Surface this
  in findings — the patch is "installed" but not "active".

### Session Manager data path

- Control plane: `ssm:StartSession` API → returns a `SessionId` and a
  pre-signed WebSocket URL.
- Data plane: the agent opens a WebSocket to `ssmmessages.<region>` and
  streams shell I/O. This is why `ssmmessages` VPC endpoint is required
  for private subnets.
- Logging: shell I/O is captured and written to S3 (full stream) and
  CloudWatch Logs (line-by-line) asynchronously. Encryption uses a
  customer-managed KMS key if specified; otherwise S3/SSE or
  CloudWatch-managed keys.
- `TerminateSession` revokes active access immediately; the WebSocket
  drops within seconds.

### Agent version feature matrix (reference)

| Agent version | Notable capability added |
|---|---|
| v2.3.12.0 | Session Manager GA |
| v2.3.372.0 | Port forwarding via Session Manager |
| v3.0.xxx | New DynamoDB-backed control plane (faster `DescribeInstanceInformation` convergence) |
| v3.1.xxx | macOS support (host-level registration) |

An agent older than v2.3.12.0 cannot do Session Manager regardless of
IAM — flag as CONFIG_GAP even if `PingStatus: Active`.
## Recent AWS features 2024-2026 (moved from SKILL.md)

- **SSM Quick Setup (2024):** Quick Setup provides pre-configured SSM baselines (patch policies, session manager, inventory) deployable via CloudFormation. Auditors should verify that Quick Setup configurations match organizational baselines and that Quick Setup-managed resources are not locally overridden.
- **Session Manager port forwarding and SSH proxy (2024-2025):** Enhanced Session Manager with native SSH proxy support and port forwarding without requiring bastion hosts. Auditors should verify that Session Manager logging is enabled for port-forwarding sessions — without logging, port-forwarding creates an unmonitored access path.
- **Hybrid Activator (2024):** SSM Hybrid Activator enables on-premises servers and edge devices to be managed by SSM. Auditors should verify that hybrid-activated instances have appropriate IAM service roles and that the activation code is not shared across environments.
- **Patch baseline enhancements (2024-2025):** Enhanced patch baselines with Amazon Linux 2023 support, Debian/Ubuntu package manager improvements, and patch compliance reporting. Auditors should verify that patch baselines cover all managed OS types in the fleet.
- **SSM Document versioning (2024):** SSM Documents now support versioning. Auditors should verify that association documents reference a specific version (not `$LATEST`) for production stability.
