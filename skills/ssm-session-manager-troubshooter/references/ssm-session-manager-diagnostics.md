# SSM Session Manager Diagnostics Reference

Supplementary reference for the SSM Session Manager Troubleshooter
skill. Use when diagnosing session failures, picking the right
diagnostic command, interpreting SSM agent log entries, or mapping
a symptom to its root cause.

## Diagnostic commands (quick lookup)

| Command | Use | Key fields |
|---|---|---|
| `aws ssm describe-sessions` | Session history + state | `SessionId`, `State`, `StartDate`, `EndDate`, `Duration`, `TerminateReason` |
| `aws ssm describe-instance-information` | Instance coverage + agent state | `PingStatus`, `LastPingDateTime`, `AgentVersion`, `IsLatestVersion`, `PlatformType` |
| `aws ssm get-connection-status` | Per-target live session state | `Status` (`connected` / `not-connected`) |
| `aws ssm describe-instance-properties` | Custom-property-based targeting | `Properties`, `InstanceType`, `PlatformType` |
| `aws ssm start-session` | Start a session (interactive, port-fwd, SSH) | `SessionId`, `Target`, `DocumentName` |
| `aws ssm terminate-session` | End a session | `SessionId` |
| `aws ssm get-document` | Read session-preferences document | `SSM-SessionManagerRunShell` defaults, KMS key, S3 bucket, CWL group |
| `aws ssm describe-document` | Document metadata | `DefaultVersion`, `PlatformTypes`, `SchemaVersion` |
| `aws ec2 describe-instances` | EC2 metadata + IAM profile + key pair | `State.Name`, `IamInstanceProfile.Arn`, `KeyName`, `VpcId`, `SubnetId` |
| `aws ec2 describe-vpc-endpoints` | Session Manager endpoints for private subnets | `ServiceName`, `State`, `SubnetIds`, `PrivateDnsEnabled` |
| `aws ec2 describe-key-pairs` | EC2 key pair inventory | `KeyName`, `KeyType` |
| `aws ec2 describe-security-groups` | Endpoint SG / instance SG audit | `IpPermissions` (inbound), `IpPermissionsEgress` (outbound) |
| `aws ec2 describe-route-tables` | Subnet route to endpoint/NAT | `Routes[*].[DestinationCidrBlock,GatewayId]` |
| `aws iam list-attached-role-policies` | Instance role policy inventory | `AttachedPolicies[*].PolicyName` |
| `aws iam simulate-principal-policy` | Test IAM without policy change | `EvalDecision`, `MatchedStatements` |
| `aws kms describe-key` | KMS key state for session encryption | `KeyState` (`Enabled` / `Disabled`), `MultiRegion` |
| `aws kms get-key-policy` | KMS key policy (cross-account check) | `Statement[*].Principal`, `Action` |
| `aws sts get-caller-identity` | Caller ARN (IAM layer) | `Arn`, `Account` |

## Session state values (describe-sessions)

| State | Meaning | Action |
|---|---|---|
| `Active` | Session is currently running | Use `get-connection-status` to verify the live channel |
| `Terminated` | Session ended normally or via disconnect | Inspect `TerminateReason` for the cause |
| `History` | Older session (past retention) | Limited detail; rely on CloudTrail for older sessions |

## TerminateReason values (root-cause signals)

| TerminateReason | Meaning | Diagnostic path |
|---|---|---|
| `UserTerminated` | Operator ran `terminate-session` or closed the client | Confirm intentional; no fix |
| `ConnectionLost` | Network drop, agent crash, or NAT idle | Step 7 (SessionDisconnects); audit network path |
| `IdleDisconnectTimeout` | `idleDisconnectTimeout` reached | Raise the timeout in session prefs |
| `MaxSessionDuration` | `maxSessionDuration` reached (default 60 min) | Raise the limit if legitimate long sessions |
| `ServiceError` | SSM-side failure | ESCALATE with session-id to AWS Support |

## 4-layer Session Manager health check (detailed)

1. **Client layer** - `session-manager-plugin` installed, current
   (>= 1.2.x), `~/.ssm/` directory writable and not corrupted.
   Verify with `session-manager-plugin --version` and
   `ls -la ~/.ssm/logs/`.

2. **IAM layer** - caller identity has `ssm:StartSession` on both
   the instance resource AND the `SSM-SessionManagerRunShell` (or
   `AWS-StartPortForwardingSession`) document. Instance role has
   `AmazonSSMManagedInstanceCore` (which grants `ssmmessages:*`).
   Verify with `simulate-principal-policy`.

3. **Connectivity layer** - instance can reach `ssm.`, `ssmmessages.`,
   and `ec2messages.` endpoints. For private subnets, verify all
   three VPC endpoints exist with `PrivateDnsEnabled: true` and the
   endpoint SG allows TCP/443 from the instance subnet CIDR.

4. **Agent layer** - `amazon-ssm-agent` running,
   `AgentVersion` >= 2.3.12.0 (Session Manager floor),
   `IsLatestVersion: true`, `PingStatus: Active` with
   `LastPingDateTime` within the last 5 minutes.

If all four layers pass, the issue is session-specific (port config,
shell config, KMS, idle timeout, or latest-feature integration).
Move to Steps 2-8.

## Common error signatures (from CLI / agent log)

| Signature | Layer | Root cause | Fix |
|---|---|---|---|
| `session-manager-plugin is not found` | Client | Plugin missing | Install via official installer |
| `OperationalError: daemon error` | Client | Plugin corrupted or stale `~/.ssm/` | Clear `~/.ssm/`, restart CLI |
| `TargetNotConnected` | Agent / connectivity | Agent offline or `ssmmessages.` blocked | 4-layer check |
| `AccessDeniedException: ssm:StartSession` | IAM | Caller identity policy gap | Add `ssm:StartSession` on instance + document resources |
| `AccessDeniedException: ssmmessages:CreateControlChannel` | IAM | Instance role missing `AmazonSSMManagedInstanceCore` | Attach policy |
| `AccessDeniedException: kms:GenerateDataKey` | IAM (KMS) | Cross-account key policy gap | Add source-account principal to key policy |
| `bind: address already in use` | Client (port fwd) | Local port occupied | `lsof -i :<port>`; free the port |
| `InvalidParameters: portNumber` | Client | JSON parameter not stringified | Use `'{"portNumber":["22"]}'` |
| `Session ended with error: shell not found` | Agent | Default shell missing or `/etc/passwd` shell is `/sbin/nologin` | Install shell or update prefs document |
| `mgs worker exited` | Agent | Agent crash / OOM | Upgrade agent; check `dmesg` and CloudWatch memory |
| `Token has expired` | Client (SSO) | SSO session timed out | Re-authenticate SSO |
| `EmptyInstanceID` | Agent | New instance still bootstrapping | Wait 5-10 min |
| `ThrottlingException` | SSM service | Rate-limited on session start | Back off; reduce concurrent sessions |

## SSM agent log locations

| OS | Path |
|---|---|
| Linux (most) | `/var/log/amazon/ssm/amazon-ssm-agent.log` |
| Linux (AL2023 / snap) | `/var/snap/amazon-ssm-agent/current/amazon-ssm-agent.log` |
| Windows | `C:\ProgramData\Amazon\SSM\Logs\amazon-ssm-agent.log` |

## session-manager-plugin log locations (client-side)

| OS | Path |
|---|---|
| macOS / Linux | `~/.ssm/logs/sessionmanagerplugin.log` |
| Windows | `%USERPROFILE%\.ssm\logs\sessionmanagerplugin.log` |

## Session Manager VPC endpoint requirements

| Endpoint service name | Used for |
|---|---|
| `com.amazonaws.<region>.ssm` | SSM API (describe, start-session) |
| `com.amazonaws.<region>.ssmmessages` | Session data channel (the live session traffic) |
| `com.amazonaws.<region>.ec2messages` | Agent-to-SSM messaging (commands, associations) |

**All three are required for fully-private Session Manager.**
`PrivateDnsEnabled: true` on each endpoint is the default and
recommended. The endpoint SG must allow TCP/443 inbound from the
instance subnet CIDR.

## Session Manager preferences document

`SSM-SessionManagerRunShell` is the default session-preferences
document. Key fields:

| Field | Default | Effect |
|---|---|---|
| `schemaVersion` | `1.0` | Document schema |
| `idleDisconnectTimeout` | `1200` (20 min) | Auto-disconnect on idle |
| `maxSessionDuration` | `60` (min) | Hard session cap |
| `shellProfile.windows` | `PowerShell` | Default Windows shell |
| `shellProfile.linux` | (empty) | Default Linux shell (uses `/etc/passwd`) |
| `kmEncryptionKey` | (none) | Customer-managed KMS key for session encryption |
| `cloudWatchStreamingEnabled` | `false` | Stream session output to CloudWatch Logs |
| `cloudWatchLogGroupName` | (none) | CWL group name |
| `s3EncryptionEnabled` | `false` | Encrypt S3 archive |
| `outputS3BucketName` | (none) | S3 archive bucket |

## IAM actions for Session Manager (caller identity)

| Action | Resource | Why |
|---|---|---|
| `ssm:StartSession` | Instance + document | Start the session |
| `ssm:GetConnectionStatus` | Instance | Check live state |
| `ssm:DescribeInstanceInformation` | `*` | Discover target |
| `ssm:DescribeSessions` | `*` | Session history |
| `ssm:TerminateSession` | Session (scoped to caller) | End own sessions |
| `ssmmessages:CreateControlChannel` | Instance | Session control plane |
| `ssmmessages:CreateDataChannel` | Instance | Session data plane |
| `ssmmessages:OpenControlChannel` | Instance | Open control channel |
| `ssmmessages:OpenDataChannel` | Instance | Open data channel |
| `kms:GenerateDataKey` (if KMS) | Key | Session encryption |
| `kms:Decrypt` (if KMS) | Key | Session decryption |
| `logs:CreateLogStream` (if CWL) | Log group | Session streaming |
| `logs:PutLogEvents` (if CWL) | Log group | Session streaming |
| `s3:PutObject` (if S3 archive) | Bucket | Session archive |

The managed policy `ssm-sessionmanager-console-perm` covers most of
these for console users. CLI-only users typically need a custom
identity policy.

## IAM actions for Session Manager (instance role)

`AmazonSSMManagedInstanceCore` grants all required `ssm:`, `ssmmessages:`,
and `ec2messages:` actions on the instance's own resources. If session
encryption, CWL streaming, or S3 archive is enabled, the instance role
also needs the KMS / logs / S3 actions above.

## Cross-account Session Manager - required trust points

Cross-account sessions require THREE independent grants:

1. **Source-account caller identity policy** - allows `ssm:StartSession`
   on the target-account instance ARN and the document ARN, plus
   `sts:AssumeRole` on the target-account role.

2. **Target-account role trust policy** - the role the source caller
   assumes trusts the source-account principal.

3. **Target-account KMS key policy** (if session encryption) - the
   key grants `kms:GenerateDataKey` + `kms:Decrypt` to the
   source-account caller.

Most cross-account failures are step 3 (KMS key policy). Verify
with `get-key-policy` and check the `Principal` list.

## Session Manager vs Run Command vs SSH

| Feature | Session Manager | Run Command | Traditional SSH |
|---|---|---|---|
| Inbound port | None | None | 22 (or custom) |
| IAM requirement | `ssm:StartSession` + `ssmmessages:*` | `ssm:SendCommand` | (none from AWS) |
| Interactive shell | Yes | No | Yes |
| Port forwarding | Yes | No | Yes |
| Audit (CWL/S3) | Yes (if enabled) | Yes (via output) | No (unless configured) |
| Agent requirement | >= 2.3.12.0 | >= 2.0.x | None |
| Cross-account | Yes (with KMS + trust) | Yes | Via bastion |

If the operator opens port 22 to "make Session Manager work," they
are using traditional SSH, not Session Manager. Verify the
session-manager-plugin is actually the transport by inspecting
`~/.ssh/config` for the `ProxyCommand aws ssm start-session` line.

## Diagnostic flowchart (high-level)

```
START: Session Manager session problem reported
|
+- Instance appears in describe-instance-information?
|  +- No -> Step 2 (TargetNotReachable) - 4-layer check
|  +- Yes -> Continue
|
+- session-manager-plugin --version succeeds?
|  +- No -> Step 3 (SessionFailsToStart) - install plugin
|  +- Yes -> Continue
|
+- simulate-principal-policy: ssm:StartSession allowed?
|  +- No -> Step 3 (SessionFailsToStart) - IAM gap
|  +- Yes -> Continue
|
+- Symptom category?
|  +- TargetNotReachable -> Step 2
|  +- SessionFailsToStart -> Step 3
|  +- PortForwardingFails -> Step 4
|  +- ShellAccessFails -> Step 5
|  +- VpcConnectivity -> Step 6
|  +- SessionDisconnects -> Step 7
|  +- LatestFeature -> Step 8
```

## CloudTrail events for Session Manager diagnosis

| EventName | What it tells you |
|---|---|
| `StartSession` | Caller attempted a session (look for `errorMessage`) |
| `TerminateSession` | Session ended (look for `sessionId`) |
| `GetConnectionStatus` | Caller checked instance live state |
| `CreateControlChannel` | Data-channel setup attempt (ssmmessages) |
| `AccessDenied` | IAM or KMS gap (visible in `errorMessage`) |

```bash
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=EventName,AttributeValue=StartSession \
  --start-time $(date -u -v-1H +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --query 'Events[*].[EventTime,Username,ResourceName]' --output table
```
