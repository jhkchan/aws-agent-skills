---
name: ssm-session-manager-troubleshooter
description: 'Diagnoses AWS Systems Manager (SSM) Session Manager failures via a systematic 7-symptom decision tree: target instance not reachable (SSM agent not running, not managed, wrong region), session fails to start (IAM role missing ssm:StartSession, session-manager console permission not attached), port forwarding fails (local port in use, SSH config conflict), shell access fails (SSM agent version too old, shell not configured), VPC connectivity issues (SSM endpoints not configured for private instances), session disconnects (network timeout, idle disconnect), and latest features (Session Manager with key pairs, cross-account sessions). Maps each symptom to root cause via diagnostic commands and specific fixes. Emits ROOT_CAUSE_FOUND with a fix plan, NEED_MORE_INFO with the next diagnostic, or ESCALATE with the escalation path. Use when a Session Manager session fails to start, drops mid-session, cannot port-forward, or shell access errors out.'
license: Apache-2.0
compatibility: Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). No AWS CLI required for offline diagnosis. Live- account troubleshooting uses aws ssm describe-sessions, describe-instance-information, get-connection-status, start-session, terminate-session, describe-instance-properties, aws ec2 describe-instances, describe-vpc-endpoints, describe-instance-profile, aws iam list-attached-role-policies, simulate-principal-policy, and CloudTrail queries (AWS CLI v2, SSO or...
metadata:
  domain: aws-cloudops
  complexity: medium
  requires_llm: 'true'
  phase: '2'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: Management
  task_type: troubleshoot
  skill_class: capability
  lifecycle_status: active
  verdict_shape: ROOT_CAUSE_FOUND | NEED_MORE_INFO | ESCALATE
  when_to_use: 'Diagnosing a Systems Manager Session Manager session that fails to start, drops mid-session, cannot establish port forwarding, returns a shell-access error, or cannot reach a target instance. Covers the seven primary symptom categories: target not reachable, session fails to start, port forwarding fails, shell access fails, VPC/endpoint connectivity, session disconnects, and latest-feature integration (key pairs, cross-account). Use when `aws ssm start-session` errors out, the console "Start session" button greys out or returns "TargetNotConnected", a port-forwarding tunnel won''t bind, or a session drops after a few minutes of use.'
  activation_triggers: Session Manager fails, session fails to start, TargetNotConnected, target instance not reachable, session-manager-plugin, port forwarding fails, shell access fails, SSM session disconnects, session drops, IdleTimeout, ssm:StartSession denied, ssm-sessionmanager-console-perm, ssmmessages endpoint missing, SSM agent version too old, Session Manager key pair, cross-account session, start-session error, session-manager plugin not installed, Port 2222 in use
  invocation_schema: 'Input: either (a) an instance-id or target-id with observed symptom (target-not-reachable / session-fails-to-start / port- forwarding-fails / shell-access-fails / vpc-connectivity / session-disconnects / latest-feature), optionally with session-id, OR (b) live-account diagnostic output from describe-sessions, describe-instance-information, get- connection-status, etc. Output: deterministic DIAGNOSIS block per session — SYMPTOM/ROOT_CAUSE/EVIDENCE/LAYER_CHECK/FIX/ VERDICT — where VERDICT is ROOT_CAUSE_FOUND (cause identified + fix actionable), NEED_MORE_INFO (specific next diagnostic cited), or ESCALATE (requires AWS Support or out-of-band action).'
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  keywords: Systems Manager, SSM, Session Manager, session fails to start, target not reachable, port forwarding, shell access, session disconnects, IdleTimeout, ssmmessages, ec2messages, ssm:StartSession, ssm-sessionmanager-console-perm, AmazonSSMManagedInstanceCore, session-manager-plugin, cross-account session, SSH proxy, KMS session encryption, VPC endpoints, SSM agent version
  tags: ssm, systems-manager, session-manager, management, troubleshoot, port-forwarding, diagnostic
---

# SSM Session Manager Troubleshooter

## Mindset

A Session Manager session is a four-layer chain: **client** (the
session-manager-plugin running on the operator's machine), **IAM**
(the caller has `ssm:StartSession` AND the target role trusts the
session channel), **connectivity** (the target can reach the
`ssmmessages.` control plane and the data channel), and **agent**
(SSM Agent >= 2.3.12.0 running with the session-manager worker
enabled). Most "session fails" tickets are one of these layers
masquerading as a Session Manager bug. Diagnose the layer first,
then the session-specific config.

> Moved to [references/advanced-patterns.md](references/advanced-patterns.md#mindset--operating-rules).
> The 4-layer gate (client/IAM/connectivity/agent), describe-sessions + describe-instance-information as source of truth, ssmmessages. as the Session-Manager-specific endpoint.

## Quick navigation

| You want to... | Go to |
|---|---|
| Run the 4-layer health check first (recommended) | Step 1 |
| Diagnose target instance not reachable | Step 2 |
| Diagnose session fails to start (IAM / plugin) | Step 3 |
| Diagnose port forwarding fails | Step 4 |
| Diagnose shell access fails | Step 5 |
| Diagnose VPC connectivity / endpoint issues | Step 6 |
| Diagnose session disconnects mid-session | Step 7 |
| Diagnose latest-feature issues (key pairs, cross-account) | Step 8 |
| Map symptom to root cause quickly | Appendix A |
| Avoid misdiagnosis pitfalls | Anti-Patterns |

## STRICT output contract

Every diagnosis MUST emit the exact DIAGNOSIS block with all fields
populated (no empty fields, no omitted sections, no reordering).
All four LAYER_CHECK lines (Client, IAM, Connectivity, Agent) are
mandatory — even when the failure is session-specific.

Verdict-specific rules:
- `ROOT_CAUSE_FOUND` -> ROOT_CAUSE names a single specific cause; EVIDENCE cites at least one failing API signal; FIX is actionable CLI.
- `NEED_MORE_INFO` -> ROOT_CAUSE is "Pending diagnosis - <what is known>"; NEXT_STEP cites the exact next command.
- `ESCALATE` -> ESCALATION_PATH names the recipient and the out-of-band action required.

```text
DIAGNOSIS: <reference>
INSTANCE: <instance-id or target-id>
SESSION: <session-id or "none — not started">
SYMPTOM: TargetNotReachable | SessionFailsToStart | PortForwardingFails | ShellAccessFails | VpcConnectivity | SessionDisconnects | LatestFeature
ROOT_CAUSE: <specific cause cited>
EVIDENCE:
  - <diagnostic signal 1>
  - <diagnostic signal 2>
LAYER_CHECK:
  - Client: <PASS | FAIL - reason>
  - IAM: <PASS | FAIL - reason>
  - Connectivity: <PASS | FAIL - reason>
  - Agent: <PASS | FAIL - reason>
FIX:
  - <action 1 with CLI snippet>
  - <action 2 ...>
VERIFICATION:
  - <command to confirm fix>
VERDICT: ROOT_CAUSE_FOUND | NEED_MORE_INFO | ESCALATE
NEXT_STEP: <if NEED_MORE_INFO, the specific next diagnostic>
ESCALATION_PATH: <if ESCALATE, the recommended path>
```

## Critical rules at a glance

> Moved to [references/advanced-patterns.md](references/advanced-patterns.md#critical-rules-at-a-glance).
> 4-layer health check first, describe-instance-information over console, ssmmessages endpoint is Session-Manager-specific, ssm-sessionmanager-console-perm separate from ssm:StartSession, IdleDisconnectTimeout default 20 min / NAT idle 350 s.

## NEVER (top 5)

- **NEVER** diagnose a session failure without first running the 4-layer health check. Most "session fails" tickets are coverage gaps in IAM, connectivity, or agent.
- **NEVER** assume `PingStatus: Active` means Session Manager will work. Active only confirms the agent pings `ssm.<region>`; Session Manager also needs `ssmmessages.<region>` reachability and agent >= 2.3.12.0. Always pair with agent-version and endpoint checks.
- **NEVER** confuse a client-side `session-manager-plugin is not installed` error with a server-side SSM problem. If the error message originates from the local AWS CLI, route to the client layer first.
- **NEVER** recommend restarting the instance as the first remediation for session failures. Restart drops the agent, breaks in-flight sessions, and masks the real cause. Modify-then-test (update agent, attach policy, deploy endpoint) preserves targeting.
- **NEVER** emit `VERDICT: NEED_MORE_INFO` without a `NEXT_STEP` naming a specific diagnostic command. Generic phrases like "investigate further" are not acceptable.

## Expert heuristic

> Moved to [references/advanced-patterns.md](references/advanced-patterns.md#expert-heuristic).
> Fast routing: TargetNotConnected in 1-2 s = IAM/agent registration; predictable drops = idle timeout; plugin OperationalError = client side; bastion-dependent = client environment; port-forward instant close = local port conflict or ProxyCommand; cross-account-only = trust/KMS key policy.

## Pre-flight: data requirements

| Input | Source | Why |
|---|---|---|
| Instance-id or target-id | Console / `describe-instance-information` | Drives all diagnostic commands |
| Observed symptom | Console / CLI error / alert | Routes to the right diagnostic branch |
| Caller identity (ARN) | `aws sts get-caller-identity` | Verifies `ssm:StartSession` is granted to the right principal |
| Region | Console | Required for all CLI calls; endpoints are region-scoped |
| Session-id (if available) | Console / `describe-sessions` | For mid-session disconnect diagnosis |
| Recent CLI output (if any) | `describe-sessions`, `describe-instance-information` | Speeds up diagnosis |
| Session-manager-plugin version (if any) | `session-manager-plugin --version` | Client-layer check |
| SSM agent log excerpt (if any) | `/var/log/amazon/ssm/amazon-ssm-agent.log` | For agent-side session errors |

**If the input is malformed** (no instance-id, ambiguous symptom),
emit:

```text
DIAGNOSIS: <reference>
INSTANCE: unknown
SESSION: unknown
SYMPTOM: unknown
ROOT_CAUSE: Pending diagnosis - required inputs missing.
EVIDENCE:
  - No instance-id or target-id supplied.
LAYER_CHECK:
  - Client: unknown
  - IAM: unknown
  - Connectivity: unknown
  - Agent: unknown
FIX: (pending inputs)
VERIFICATION: (pending fix)
VERDICT: NEED_MORE_INFO
NEXT_STEP: Re-supply: instance-id or target-id, the observed
  symptom (target-not-reachable / session-fails-to-start /
  port-forwarding-fails / shell-access-fails / vpc-connectivity
  / session-disconnects / latest-feature), the caller identity
  ARN, and the region.
ESCALATION_PATH: None
```

## Process - Diagnostic decision tree (apply in order)

### Step 0: Expert knowledge - non-obvious Session Manager behaviors

> Moved to [references/advanced-patterns.md](references/advanced-patterns.md#step-0-expert-knowledge---non-obvious-session-manager-behaviors).
> ssmmessages endpoint specifics, agent >= 2.3.12.0 mgs floor, console-perm vs CLI, StartSession resource scoping, plugin separate from CLI, SSH-over-SSM document scoping, IdleDisconnectTimeout document override, NAT 350 s drops, local port conflicts, cross-account KMS key policy, mgs region match, stale ~/.ssm state, no inbound 22/3389 needed.

### Step 1: The 4-layer Session Manager health check (run FIRST)

Before any session-specific diagnosis, confirm all four layers. A
failing layer invalidates all downstream diagnosis.

**Layer 1 - Client (session-manager-plugin installed and current):**

```bash
session-manager-plugin --version
# Expect: 1.2.x or newer; plugin path printed by the AWS CLI
which session-manager-plugin
```

If the plugin is missing, the CLI returns
`SessionManagerPlugin is not found` immediately. Install via the
official installer for the platform.

**Layer 2 - IAM (caller has ssm:StartSession, target role trusts the channel):**

```bash
aws sts get-caller-identity --query 'Arn' --output text
aws iam simulate-principal-policy --policy-source-arn <caller-arn> \
  --action-names ssm:StartSession ssm:GetConnectionStatus ssm:TerminateSession \
  --resource-arns arn:aws:ssm:<region>:<account>:instance/<instance-id> \
  --query 'EvaluationResults[*].[EvalActionName,EvalDecision]' --output table
aws ec2 describe-instances --instance-ids <instance-id> \
  --query 'Reservations[*].Instances[*].IamInstanceProfile.Arn' --output text
aws iam list-attached-role-policies --role-name <instance-role-name> --output text
```

Flags: missing `ssm:StartSession` = identity policy gap. Instance
role missing `AmazonSSMManagedInstanceCore` (which grants
`ssmmessages:*`) = target-side gap. Console-only callers also need
`ssm-sessionmanager-console-perm`.

**Layer 3 - Connectivity (target can reach ssmmessages endpoint):**

For private-subnet instances, confirm the three required VPC endpoints:

```bash
aws ec2 describe-vpc-endpoints \
  --filters Name=vpc-id,Values=<vpc-id> \
  Name=service-name,Values=com.amazonaws.<region>.ssm,com.amazonaws.<region>.ssmmessages,com.amazonaws.<region>.ec2messages \
  --query 'VpcEndpoints[*].[ServiceName,State]' --output table
```

For internet-egress instances, verify the security group allows
HTTPS/443 outbound to SSM CIDRs.

**Layer 4 - Agent (running, current, and pinging):**

```bash
aws ssm describe-instance-information \
  --instance-information-filter-list Key=InstanceIds,ValueSet=<instance-id> \
  --query 'InstanceInformationList[*].[PingStatus,LastPingDateTime,AgentVersion,IsLatestVersion,PlatformType]' --output table
```

Flags: `ConnectionLost`/`Inactive` = Layer 2 or 3 failure.
`AgentVersion` < 2.3.12.0 = agent cannot run Session Manager.
`LastPingDateTime` > 5 minutes = flapping agent.

**If any layer fails, fix the layer FIRST.** Most session failures
resolve when coverage is restored. Specifically:
- Layer 1 fails -> install/upgrade `session-manager-plugin`.
- Layer 2 fails -> attach `AmazonSSMManagedInstanceCore` to instance profile; add `ssm:StartSession` to caller identity policy.
- Layer 3 fails -> deploy `ssmmessages.<region>` VPC endpoint or fix security group outbound.
- Layer 4 fails -> restart agent, upgrade via `AWS-UpdateSSMAgent`, or wait 5 min for a freshly-launched instance to bootstrap.

### Step 2: Diagnose target instance not reachable

**Symptom:** `aws ssm start-session` returns `TargetNotConnected` or
the console shows the instance as disconnected.

```bash
aws ssm describe-instance-information \
  --instance-information-filter-list Key=InstanceIds,ValueSet=<instance-id> \
  --query 'InstanceInformationList[*].[PingStatus,LastPingDateTime,AgentVersion,IsLatestVersion,PlatformType]' --output table
aws ssm get-connection-status --target <instance-id> \
  --query 'Status' --output text
```

| Cause | Diagnostic signal | Fix |
|---|---|---|
| SSM agent not running | `PingStatus: Inactive` or `ConnectionLost`; `LastPingDateTime` stale | Run on-host: `systemctl status amazon-ssm-agent`; restart or install |
| Instance not managed | `describe-instance-information` returns empty for the instance | Attach `AmazonSSMManagedInstanceCore` instance profile; deploy endpoints |
| Wrong region | Instance visible in `ec2 describe-instances --region us-west-2` but not `--region us-east-1` | Re-run `start-session` with the correct `--region` |
| Instance stopped/terminated | `ec2 describe-instances` shows `stopped`/`terminated` | Start or recreate the instance |
| Hybrid activation expired | `mi-*` instance; `describe-activations` shows `Expired: true` | Create new activation; re-register on-host (ESCALATE - requires on-host access) |
| Fresh launch (< 5 min) | `LaunchTime` within last 5 minutes | Wait 5-10 minutes; do not flag as unreachable |

**VERDICT:** ROOT_CAUSE_FOUND when PingStatus/activation signal
identifies a specific cause; NEED_MORE_INFO when the instance is
reachable by EC2 but not SSM and agent log is unavailable.

### Step 3: Diagnose session fails to start (IAM / plugin)

**Symptom:** `start-session` returns `AccessDeniedException`,
`session-manager-plugin is not found`, or the console "Start session"
button is greyed out.

```bash
aws sts get-caller-identity --query 'Arn' --output text
aws iam simulate-principal-policy --policy-source-arn <caller-arn> \
  --action-names ssm:StartSession \
  --resource-arns "arn:aws:ssm:<region>:<account>:instance/<instance-id>" "arn:aws:ssm:<region>:<account>:document/SSM-SessionManagerRunShell" \
  --query 'EvaluationResults[*].[EvalActionName,EvalDecision]' --output table
session-manager-plugin --version
```

| Cause | Diagnostic signal | Fix |
|---|---|---|
| Caller lacks `ssm:StartSession` | `simulate-principal-policy` returns `Denied` for `ssm:StartSession` | Add `ssm:StartSession` on the instance + `SSM-SessionManagerRunShell` document to caller policy |
| Console user lacks `ssm-sessionmanager-console-perm` | Caller has `ssm:StartSession` but console still greys out | Attach `AmazonSSMManagedInstanceCore` or `ssm-sessionmanager-console-perm` managed policy |
| session-manager-plugin not installed | CLI error: `session-manager-plugin is not found` | Install plugin via official installer |
| session-manager-plugin outdated | Plugin version < 1.1.x; `OperationalError` on start | Upgrade plugin |
| `ssm:StartSession` scoped to wrong document | Policy allows `ssm:StartSession` on `document/AWS-StartPortForwardingSession` only; user runs interactive shell | Add `document/SSM-SessionManagerRunShell` to the resource list |
| Target instance role missing `ssmmessages:*` | `list-attached-role-policies` lacks `AmazonSSMManagedInstanceCore` | Attach `AmazonSSMManagedInstanceCore` to the instance profile role |
| KMS key policy blocks session encryption | `kms:GenerateDataKey` denied for the caller; session-prefs document references the key | Add `kms:GenerateDataKey` + `kms:Decrypt` for the caller in the key policy |

**VERDICT:** ROOT_CAUSE_FOUND when `simulate-principal-policy` or
plugin check identifies a specific cause; NEED_MORE_INFO when IAM
and client both pass but session still fails (fetch session-manager
plugin logs from `~/.ssm/logs/`).

### Step 4: Diagnose port forwarding fails

**Symptom:** `aws ssm start-session --document-name AWS-StartPortForwardingSession --parameters '{"portNumber":["22"]}'` fails or the tunnel closes immediately.

> Moved to [references/diagnostic-commands.md](references/diagnostic-commands.md#step-4--port-forwarding-diagnostic-commands).
> describe-document AWS-StartPortForwardingSession, simulate-principal-policy on the port-forwarding document, and the lsof local-port probe.

| Cause | Diagnostic signal | Fix |
|---|---|---|
| Local port in use | `lsof -i :<port>` returns a PID; session log shows `bind: address already in use` | Free the port (`kill <pid>`) or use a different `localPortNumber` |
| `~/.ssh/config` `ProxyCommand` conflict | SSH config has `ProxyCommand aws ssm start-session ...` that double-routes | Remove or comment the ProxyCommand; use direct `aws ssm start-session` for the tunnel |
| `ssm:StartSession` not scoped to `AWS-StartPortForwardingSession` | `simulate-principal-policy` returns `Denied` on that document | Add `AWS-StartPortForwardingSession` to the allowed document resource list |
| `portNumber` parameter malformed | `InvalidParameters: portNumber must be a string` | Pass JSON with string values: `'{"portNumber":["22"],"hostName":["localhost"]}'` |
| `hostName` targets unreachable host | Tunnel binds but SSH/HTTP connect times out | Verify the target host is reachable from the instance (`ssm send-command` with `curl`/`nc`) |
| Remote service not listening | Tunnel binds; `nc -zv <host> <port>` from the instance fails | Start the remote service or correct the port |

**VERDICT:** ROOT_CAUSE_FOUND when `lsof`/SSH config/`simulate-principal-policy`
identifies a specific cause; NEED_MORE_INFO when the tunnel binds
and the remote port is open but the application still fails
(capture the application-layer error).

### Step 5: Diagnose shell access fails

**Symptom:** session starts but the shell is unresponsive, returns
`This shell is not configured`, or the agent log shows a shell-
init error.

```bash
aws ssm describe-instance-information \
  --instance-information-filter-list Key=InstanceIds,ValueSet=<instance-id> \
  --query 'InstanceInformationList[*].[AgentVersion,PlatformType]' --output table
aws ssm send-command --instance-ids <instance-id> \
  --document-name AWS-RunShellScript \
  --parameters 'commands=["echo $SHELL","cat /etc/shells","ls -l /bin/bash"]' \
  --query 'Command.CommandId' --output text
```

| Cause | Diagnostic signal | Fix |
|---|---|---|
| SSM agent version too old | `AgentVersion` < 2.3.12.0 | Upgrade agent via `AWS-UpdateSSMAgent` or OS package manager |
| Default shell not configured | `/etc/passwd` for the ssm-user has `/sbin/nologin` or empty | Set `shell.legacyDomainShell` in session prefs or fix the user's shell |
| `ssm-user` not created (Linux) | Agent log shows `unable to find user ssm-user` | Upgrade agent (>= 2.3.12.0 auto-creates it); or `useradd ssm-user` manually |
| Shell binary missing | `ls /bin/bash` returns no such file | Install bash (or change the configured shell to `/bin/sh`) |
| Session prefs document points to missing shell | `SSM-SessionManagerRunShell` references `/bin/fish` which is not installed | Update the prefs document `shell.runAsElevated` and shell path |
| Windows: OpenSSH not installed | `Get-WindowsCapability` shows `OpenSSH.Server` not installed | Install OpenSSH or use the default PowerShell shell path |
| Disk full on the instance | Agent log shows `no space left on device` during session init | Free disk space; the agent needs working space for the session worker |

**VERDICT:** ROOT_CAUSE_FOUND when agent version or shell config
identifies a specific cause; NEED_MORE_INFO when the session starts
and the shell runs but specific commands fail (route to the
application, not Session Manager).

### Step 6: Diagnose VPC connectivity / endpoint issues

**Symptom:** instance is reachable from EC2 (security groups, route
tables OK) but `PingStatus: ConnectionLost`; sessions never start.

```bash
aws ec2 describe-vpc-endpoints \
  --filters Name=vpc-id,Values=<vpc-id> \
  --query 'VpcEndpoints[*].[ServiceName,State,VpcEndpointType,SubnetIds]' --output table
aws ec2 describe-security-groups --group-ids <endpoint-sg-id> \
  --query 'SecurityGroups[*].IpPermissions[*].[FromPort,ToPort,IpRanges]' --output table
aws ec2 describe-route-tables --filters Name=vpc-id,Values=<vpc-id> \
  --query 'RouteTables[*].Routes[*].[DestinationCidrBlock,GatewayId]' --output table
```

| Cause | Diagnostic signal | Fix |
|---|---|---|
| `ssmmessages.` endpoint missing | `describe-vpc-endpoints` does not include `com.amazonaws.<region>.ssmmessages` | Create the `ssmmessages` interface endpoint in the instance VPC |
| `ec2messages.` endpoint missing | Same check for `ec2messages` | Create the `ec2messages` interface endpoint |
| Endpoint SG blocks 443 from instance subnet | Endpoint SG ingress does not include the instance subnet CIDR on TCP/443 | Add inbound rule: TCP/443 from the instance subnet CIDR |
| Endpoint in wrong subnet | Endpoint subnets do not include the instance's AZ | Add the missing AZ subnet to the endpoint |
| NAT gateway idle timeout (350s) | Sessions drop at ~5 min 50 sec of idle | Use a keepalive (`ServerAliveInterval` in SSH-over-SSM) or switch to VPC endpoints |
| Route table lacks endpoint route | `describe-route-tables` does not show the endpoint | Add the endpoint to the relevant route table or rely on private DNS |
| Private DNS not enabled on endpoint | Endpoint `PrivateDnsEnabled: false`; instance still resolves public SSM DNS | Set `PrivateDnsEnabled=true` on the `ssm`, `ssmmessages`, and `ec2messages` endpoints |

**VERDICT:** ROOT_CAUSE_FOUND when endpoint/SG/route analysis
identifies a specific gap; NEED_MORE_INFO when the endpoint exists
and the SG is correct but the instance still cannot reach it
(run `aws ssm send-command` with `nc -vz ssmmessages.<region> 443`
to gather evidence).

### Step 7: Diagnose session disconnects mid-session

**Symptom:** session starts and works, then drops after a predictable
or variable interval.

```bash
aws ssm describe-sessions --state Terminated \
  --instance-id <instance-id> \
  --query 'Sessions[*].[SessionId,StartDate,EndDate,Duration,TerminateReason]' --output table
aws ssm describe-instance-information \
  --instance-information-filter-list Key=InstanceIds,ValueSet=<instance-id> \
  --query 'InstanceInformationList[*].[PingStatus,LastPingDateTime]' --output table
```

| Cause | Diagnostic signal | Fix |
|---|---|---|
| `IdleDisconnectTimeout` reached | `Duration` matches the prefs-doc setting (default 20 min) exactly | Raise `idleDisconnectTimeout` in `SSM-SessionManagerRunShell` or override per-session |
| NAT gateway idle timeout (350 sec) | Session drops at ~350 sec of no traffic; `TerminateReason: ConnectionLost` | Add `ServerAliveInterval 30` to SSH-over-SSM; or move to VPC endpoints |
| Network interruption (transient) | `LastPingDateTime` gap; session recovers on retry | Treat as transient; if recurring, audit network path |
| Agent crashed mid-session | Agent log shows a panic or `mgs worker exited` | Upgrade agent; check for OOM (`dmesg`, CloudWatch memory) |
| Instance CPU/memory starved | CloudWatch CPU at 100%; agent unresponsive | Resize the instance or shed load |
| Caller credential expiry (SSO) | SSO token expired mid-session; CLI shows `Token has expired` | Re-authenticate SSO; consider longer token duration |
| KMS key disabled/rotated mid-session | Session was using envelope encryption; key state changed | Verify key state; re-establish session after key enablement |
| Operator terminated by mistake | `TerminateReason: UserTerminated` | Confirm intentional; no fix |

**VERDICT:** ROOT_CAUSE_FOUND when `Duration` + `TerminateReason`
matches a known timeout/cause; NEED_MORE_INFO when the disconnect
is intermittent and agent log shows no error (instrument the
network path or run a long-running test session).

### Step 8: Diagnose latest-feature issues (key pairs, cross-account)

**Symptom:** SSH-over-Session-Manager with a key pair fails, or a
cross-account session returns `AccessDeniedException` despite the
caller having `ssm:StartSession`.

> Moved to [references/diagnostic-commands.md](references/diagnostic-commands.md#step-8--latest-feature-diagnostic-commands-key-pair-cross-account).
> describe-key-pairs, describe-instances KeyName, cross-account simulate-principal-policy, kms describe-key and get-key-policy probes.

| Cause | Diagnostic signal | Fix |
|---|---|---|
| Key pair not attached to instance | `describe-instances` shows blank `KeyName` | Launch a new instance with the key pair, or use the default Session Manager shell (no SSH key needed) |
| SSH client not using Session Manager transport | `ssh -i key.pem ec2-user@i-...` fails; SSH config lacks `ProxyCommand aws ssm start-session...` | Add the ProxyCommand to `~/.ssh/config` for `Host i-* mi-*` |
| Cross-account: KMS key policy lacks source-account principal | `get-key-policy` does not include the source-account ARN in the `Statement.Principal` | Add `kms:GenerateDataKey` + `kms:Decrypt` for the source-account caller in the target-account KMS key policy |
| Cross-account: target-account instance resource policy not scoped | Target account has not granted `ssm:StartSession` to the source-account caller | Add a resource-based or identity-based policy in the target account |
| Cross-account: STS assumed-role session name too long | `RoleSessionName` > 64 chars; SSM rejects | Use a shorter `--role-session-name` |
| Session Manager key pair on Windows | Windows instances do not consume the EC2 key pair for Session Manager | Use `AWS-StartPortForwardingSession` to RDP, or use the default PowerShell shell |
| Key pair region mismatch | Key pair exists in us-east-1 but instance is in us-west-2 | Generate or import a key pair in the correct region |

**VERDICT:** ROOT_CAUSE_FOUND when key-pair check, KMS key policy,
or trust-policy analysis identifies a specific cause; NEED_MORE_INFO
when cross-account config appears correct but the session still
fails (fetch CloudTrail `AccessDenied` event for the exact missing
action).

## Output format

The output block template above is the authoritative structure.
Violating any rule is a misdiagnosis. Two worked examples follow.

### Worked example - ROOT_CAUSE_FOUND, SessionFailsToStart (IAM gap)

```text
DIAGNOSIS: prod-bastion-session
INSTANCE: i-0abc123def456789a
SESSION: none - not started
SYMPTOM: SessionFailsToStart
ROOT_CAUSE: Caller identity lacks ssm:StartSession on the
            SSM-SessionManagerRunShell document; the identity
            policy scopes ssm:StartSession to instance resources
            only, omitting the session document resource.
EVIDENCE:
  - aws ssm start-session returned: AccessDeniedException: User arn:aws:sts::111111111111:assumed-role/DevOpsRole/jacky is not authorized to perform: ssm:StartSession
  - simulate-principal-policy on arn:aws:sts::111111111111:assumed-role/DevOpsRole/jacky: Denied for ssm:StartSession on arn:aws:ssm:us-east-1:111111111111:document/SSM-SessionManagerRunShell
LAYER_CHECK:
  - Client: PASS - session-manager-plugin 1.2.612.0 installed
  - IAM: FAIL - caller identity policy omits SSM-SessionManagerRunShell document resource
  - Connectivity: PASS - PingStatus Active, ssmmesages endpoint present
  - Agent: PASS - AgentVersion 3.3.131.0, IsLatestVersion true
FIX:
  - Add the session document to the caller identity policy:
    aws iam put-role-policy --role-name DevOpsRole --policy-name SsmSessionStart --policy-document '{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Action":["ssm:StartSession"],"Resource":["arn:aws:ssm:us-east-1:111111111111:instance/*","arn:aws:ssm:us-east-1:111111111111:document/SSM-SessionManagerRunShell"]}]}'
  - Re-run:
    aws ssm start-session --target i-0abc123def456789a --region us-east-1 --profile default
VERIFICATION:
  - aws iam simulate-principal-policy --policy-source-arn arn:aws:sts::111111111111:assumed-role/DevOpsRole/jacky --action-names ssm:StartSession --resource-arns arn:aws:ssm:us-east-1:111111111111:document/SSM-SessionManagerRunShell --query 'EvaluationResults[0].EvalDecision' --output text
  - Expect: allowed
VERDICT: ROOT_CAUSE_FOUND
NEXT_STEP: None
ESCALATION_PATH: None
```

### Worked example - NEED_MORE_INFO, SessionDisconnects (intermittent)

> Moved to [references/worked-examples.md](references/worked-examples.md#worked-example---need_more_info-sessiondisconnects-intermittent).
> Full NEED_MORE_INFO block: drops at 4m12s not aligned to any timeout; NEXT_STEP correlates sessionmanagerplugin.log with amazon-ssm-agent.log mgs entries.

### Worked example - ESCALATE, cross-account KMS key policy

> Moved to [references/worked-examples.md](references/worked-examples.md#worked-example---escalate-cross-account-kms-key-policy).
> Full ESCALATE block: target-account KMS key policy lacks the source-account principal; includes the exact key-policy statement to hand to the target-account key admin.

## Anti-Patterns - NEVER do these things

- NEVER diagnose a session failure without first running the 4-layer health check. Most "session fails" tickets are coverage gaps in client, IAM, connectivity, or agent.
- NEVER assume `PingStatus: Active` means Session Manager will work. Active only confirms the agent pings `ssm.<region>`; Session Manager also needs `ssmmessages.<region>` reachability and agent >= 2.3.12.0. Always pair with agent-version and endpoint checks.
- NEVER confuse a client-side `session-manager-plugin is not installed` error with a server-side SSM problem. If the error message originates from the local AWS CLI, route to the client layer first.
- NEVER recommend restarting the instance as the first remediation for session failures. Restart drops the agent, breaks in-flight sessions, and masks the real cause. Modify-then-test (update agent, attach policy, deploy endpoint) preserves targeting.
- NEVER emit `VERDICT: NEED_MORE_INFO` without a `NEXT_STEP` naming a specific diagnostic command. Generic phrases like "investigate further" are not acceptable.

## Pre-flight safety checks

- **MANDATORY CONFIRMATION GATE** before any state-changing operation (`start-session`, `terminate-session`, `update-document`, `create-vpc-endpoint`, `put-key-policy`).
- **`start-session` target blast radius:** confirm the instance-id before starting a session — a wrong id lands you on a different host.
- **`update-document` for session prefs:** snapshot `get-document --output json` BEFORE the update; prefs drift causes "sessions drop for everyone."
- **KMS key policy changes:** always print the existing policy first (`get-key-policy --output json`); never overwrite without a backup.
- **Cross-account work:** confirm the caller has `sts:AssumeRole` on the target-account role before diagnosing the target side.

## Appendix A - Symptom-to-cause map (quick reference)

> Moved to [references/diagnostic-commands.md](references/diagnostic-commands.md#appendix-a---symptom-to-cause-map-quick-reference).
> 21-row symptom-to-cause-to-verify table covering TargetNotReachable, SessionFailsToStart, PortForwardingFails, ShellAccessFails, VpcConnectivity, SessionDisconnects, and LatestFeature branches.

## Recent AWS features (2024-2026)

> Moved to [references/advanced-patterns.md](references/advanced-patterns.md#recent-aws-features-2024-2026).
> Key-pair SSH-over-SSM, cross-account sessions, CloudWatch Logs / S3 streaming, enhanced port forwarding and SSH proxy, ECS Exec via ssmmessages, MGS region expansion, customer-managed KMS session encryption.

## References (load on demand)

- [advanced-patterns](references/advanced-patterns.md) — Critical rules at a glance, Mindset operating rules, expert-heuristic routing, Step 0 non-obvious Session Manager behaviors, Recent AWS features (2024-2026)
- [diagnostic-commands](references/diagnostic-commands.md) — Appendix A symptom-to-cause map plus Step 4 / Step 8 probe commands moved from SKILL.md
- [ssm-session-manager-diagnostics](references/ssm-session-manager-diagnostics.md) — diagnostic command quick lookup, agent-log interpretation, symptom mapping
- [worked-examples](references/worked-examples.md) — NEED_MORE_INFO intermittent-disconnect and ESCALATE cross-account KMS examples moved from SKILL.md

## Domain

AWS CloudOps / Systems Manager Session Manager Diagnostics.

## AWS documentation

- **AWS Systems Manager Session Manager User Guide** - https://docs.aws.amazon.com/systems-manager/latest/userguide/session-manager.html
- **Setting up Session Manager** - https://docs.aws.amazon.com/systems-manager/latest/userguide/session-manager-getting-started.html
- **Session Manager prerequisites** - https://docs.aws.amazon.com/systems-manager/latest/userguide/session-manager-prerequisites.html
- **Troubleshooting Session Manager** - https://docs.aws.amazon.com/systems-manager/latest/userguide/session-manager-troubleshooting.html
- **IAM policies for Session Manager** - https://docs.aws.amazon.com/systems-manager/latest/userguide/session-manager-getting-started-iam-policy.html
- **VPC endpoints for Session Manager** - https://docs.aws.amazon.com/systems-manager/latest/userguide/session-manager-prerequisites.html#session-manager-prerequisites-vpc-endpoints
- **Port forwarding with Session Manager** - https://docs.aws.amazon.com/systems-manager/latest/userguide/session-manager-working-with-sessions-start.html#sessions-start-port-forwarding
- **Cross-account Session Manager** - https://docs.aws.amazon.com/systems-manager/latest/userguide/session-manager-cross-account.html
- **Session Manager preferences** - https://docs.aws.amazon.com/systems-manager/latest/userguide/session-manager-working-with-session-preferences.html
- **API Reference** - https://docs.aws.amazon.com/systems-manager/latest/APIReference/
- **CLI Reference** - https://docs.aws.amazon.com/cli/latest/reference/ssm/
- **session-manager-plugin (GitHub)** - https://github.com/aws/session-manager-plugin
