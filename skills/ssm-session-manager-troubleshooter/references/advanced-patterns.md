# Advanced Patterns — ssm-session-manager-troubleshooter

> Moved verbatim from SKILL.md for progressive disclosure (agentskills.io). Load on demand.

## Mindset — operating rules

- **The 4-layer health check is the upstream gate.** If any of
  client, IAM, connectivity, or agent is broken, no session can
  start. Diagnose in that order — most failures resolve before
  you reach the session-specific branches.
- **`describe-sessions` + `describe-instance-information` are the
  source of truth.** The console greys out buttons and shows a
  generic "Connection refused"; the API returns the precise
  `PingStatus`, `LastPingDateTime`, and session-state transitions.
- **`ssmmessages.` is the Session Manager-specific endpoint.**
  Many SSM health checks only verify `ssm.` and `ec2messages.` —
  Session Manager also requires `ssmmessages.<region>`. A "managed"
  instance with the other two endpoints can still fail to start a
  session.

## Critical rules at a glance

1. **Run the 4-layer health check FIRST.** Before any session-specific diagnosis, confirm: (1) session-manager-plugin installed and current on the client, (2) caller identity has `ssm:StartSession` + the target role has `ssmmessages:*` via `AmazonSSMManagedInstanceCore`, (3) target can reach `ssmmessages.<region>`, (4) SSM Agent >= 2.3.12.0 running and pinging.
2. **Use `describe-instance-information`, not the console.** The console's "Start session" button greys out for many reasons. The API returns `PingStatus`, `LastPingDateTime`, and `AgentVersion` — the actual health signals.
3. **`ssmmessages.` endpoint is Session Manager-specific.** The standard SSM health check verifies `ssm.` and `ec2messages.`; Session Manager requires all three. A "managed" instance with two endpoints still fails sessions.
4. **`ssm-sessionmanager-console-perm` is separate from `ssm:StartSession`.** Console users need both. CLI-only users need only `ssm:StartSession` + the document/instance resources in the identity policy.
5. **`IdleDisconnectTimeout` defaults to 20 minutes.** Sessions dropping at predictable intervals almost always trace to this setting or a NAT gateway idle timeout (default 350 seconds).

## Expert heuristic

- If `aws ssm start-session` returns `TargetNotConnected` within 1-2 seconds, the failure is **IAM or agent registration** (the service rejected the request before attempting a data channel). Route to Steps 2-3.
- If the session starts but drops after a predictable interval (e.g., always ~20 min or ~5 min 50 sec), the failure is **idle timeout** (Step 7) — check `IdleDisconnectTimeout` on the document and any NAT gateway idle timeout (350 sec).
- If `start-session` returns `OperationalError` or `daemon error` from the session-manager-plugin, the failure is **client-side** — the plugin is missing, out of date, or the local `~/.ssm` directory has stale state.
- If sessions work from one bastion but not another, the failure is **client environment** (plugin version, AWS CLI v1 vs v2, IAM identity of the caller) — not the target.
- If port forwarding binds but immediately closes with `session terminated`, the failure is usually a **local-port conflict** or an `~/.ssh/config` `ProxyCommand` double-routing the tunnel. Test with a fresh port above 30000.
- If only cross-account sessions fail, the failure is **the target-account trust policy or the KMS key policy** — same-account sessions do not exercise those policies.

### Step 0: Expert knowledge - non-obvious Session Manager behaviors

- **The `ssmmessages.` endpoint is Session Manager-specific.** Many health checks only verify `ssm.` and `ec2messages.`. An instance can be "managed" (associations run, Run Command works) but still fail Session Manager if `ssmmessages.<region>` is unreachable. Always check all three.
- **Agent version >= 2.3.12.0 is the Session Manager floor.** Earlier agents do not load the `mgs` (message gateway service) worker. `IsLatestVersion: true` on a 2.0.x agent still fails sessions.
- **`ssm-sessionmanager-console-perm` is a managed policy for console users only.** CLI users with `ssm:StartSession` + `ssm:GetConnectionStatus` + `ssm:DescribeInstance*` + `ssm:TerminateSession` work fine without it. Mixing the two paths produces "works in CLI, fails in console" symptoms.
- **`ssm:StartSession` resource scope matters.** A policy allowing `ssm:StartSession` on `*` works, but scoping to `arn:aws:ssm:<region>:<account>:instance/<instance-id>` fails if the caller passes a different instance-id. Verify the resource ARN matches the target.
- **The `session-manager-plugin` is a separate binary from the AWS CLI.** Installing or upgrading the AWS CLI does NOT install or upgrade the plugin. The plugin has its own release cadence.
- **SSH-over-Session-Manager requires `ssm:StartSession` with `SSM-SessionManagerRunShell` document.** If the user's policy scopes `ssm:StartSession` to a specific document that is NOT `SSM-SessionManagerRunShell`, SSH proxy fails.
- **`IdleDisconnectTimeout` in the session-preferences document overrides the account default.** Verify the document referenced by the session, not the account-level setting, when diagnosing idle disconnects.
- **NAT gateway idle timeout is 350 seconds.** Sessions that idle through the NAT gateway for > 350 sec get silently dropped by the NAT, not by SSM. This masquerades as "SSM drops my session."
- **Port forwarding requires the local port to be free.** `--parameters portNumber=2222` fails instantly with `bind: address already in use` if another process holds the port. Always probe with `lsof -i :<port>` before retrying.
- **Cross-account sessions require the KMS key policy to grant the caller account `kms:GenerateDataKey` and `kms:Decrypt`.** Same-account sessions rely on the caller identity policy; cross-account sessions also exercise the key policy. Many cross-account failures are KMS key policy, not IAM.
- **The `mgs` (message gateway service) region must match the instance region.** A VPN or Client VPN that hairpins through another region can break Session Manager even though EC2 reachability tests pass.
- **`session-manager-plugin` writes logs to `~/.ssm/logs/`.** Stale logs or a corrupted `~/.ssm/` directory can cause "OperationalError" on session start. Clearing the directory resolves it.
- **Session Manager does NOT require inbound SSH (port 22) or RDP (port 3389) on the instance security group.** If a session works only after opening 22, the operator is using traditional SSH, not Session Manager — verify the session-manager-plugin is actually the transport.

## Recent AWS features (2024-2026)

- **Session Manager key pair support (2024-2025):** Instances launched with an EC2 key pair can use SSH-over-Session-Manager without inbound port 22. Verify the instance `KeyName` is set and the client SSH config has the `ProxyCommand aws ssm start-session` for `Host i-* mi-*`.
- **Cross-account Session Manager (2024-2025):** Sessions can target instances in another account via STS assumed roles. Requires both the IAM trust AND the KMS key policy to grant the source-account principal. Most cross-account failures are KMS key policy, not IAM.
- **Session Manager streaming to CloudWatch Logs (2024):** Session output can stream to CloudWatch Logs. Verify the `SSM-SessionManagerRunShell` `cloudWatchStreamingEnabled` and the instance role has `logs:CreateLogStream`, `logs:PutLogEvents`.
- **Session Manager streaming to S3 (2024-2025):** Session output can be archived to S3. Verify the `s3EncryptionEnabled` and `outputS3BucketName` and the instance role has `s3:PutObject` on the bucket.
- **Enhanced port forwarding and SSH proxy (2024-2025):** Native SSH proxy supports `Host i-* mi-*` in `~/.ssh/config`. Verify the client uses the latest `session-manager-plugin` (>= 1.2.x) and the ProxyCommand syntax matches the plugin version.
- **Session Manager for ECS Exec (2024-2025):** ECS Exec uses Session Manager under the hood. Verify the task role has `ssmmessages:CreateControlChannel`, `CreateDataChannel`, `OpenControlChannel`, `OpenDataChannel`.
- **MGS (Message Gateway Service) region expansion (2025-2026):** New regions require `ssmmessages.<region>` endpoint deployment. Verify endpoints in all regions where sessions run.
- **Session encryption with customer-managed KMS keys (2024-2026):** Session prefs can reference a customer-managed KMS key. Verify the key is enabled and the key policy grants both the caller and the instance role.
