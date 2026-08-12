---
description: Diagnose AWS Systems Manager Session Manager failures through a thirteen-category diagnostic tree (instance registration, session timeout, agent version, IAM permissions, VPC endpoints, session document, port forwarding, shell profile, audit logs to S3, session recording, CloudWatch Logs, patch baseline, SSM document) — emits ROOT_CAUSE_IDENTIFIED with the specific failure layer or INSUFFICIENT_DATA.
nl_triggers:
  - "SSM Session Manager connection failed"
  - "SSM session timeout"
  - "SSM session times out"
  - "managed instance not showing up"
  - "instance not registered SSM"
  - "SSM Agent not running"
  - "SSM agent stopped"
  - "ssm:StartSession denied"
  - "SSM port forwarding failed"
  - "port forwarding NotSupported"
  - "channel closed Session Manager"
  - "ChannelClosedException"
  - "ssmmessages endpoint"
  - "VPC endpoint SSM missing"
  - "SSM session recording S3"
  - "SSM audit logs missing"
  - "SessionManagerRunShell"
  - "SSM Document error"
  - "SSM agent version outdated"
  - "hybrid activation expired"
  - "patch baseline blocking session"
  - "troubleshoot SSM Session Manager"
  - "diagnose SSM session"
routes_to: ssm-session-troubleshooter
---

# /aws:troubleshoot-ssm-session

Activate the `ssm-session-troubleshooter` skill and diagnose an AWS
Systems Manager Session Manager failure through the thirteen-category
diagnostic tree.

## What it does

Reads a symptom description (error message, observed behaviour,
instance/session context) plus the instance configuration, then
walks the symptom-driven diagnostic tree to a root cause with
positive evidence:

1. **Pre-flight** — instance state (`describe-instance-information`,
   `describe-instance-properties`), recent sessions
   (`describe-sessions`), session document (`get-document`), AWS
   Health (regional incidents). Short-circuits on `ConnectionLost`
   `PingStatus`, absent instance, or deprecated
   `AmazonEC2RoleforSSM` policy.
2. **Symptom entry** — map the error to one of: instance absent,
   session timeout, `AccessDeniedException` on StartSession,
   `NotSupported` for port forwarding, `InvalidDocument`, session
   opens-then-closes, audit bucket empty, CloudWatch Logs empty,
   macOS session failure.
3. **Layer-specific probes** —
   - Registration: `describe-instance-information` presence,
     `ec2 describe-instances` State and IamInstanceProfile, agent
     service status on-instance, hybrid activation validity.
   - IAM: `iam simulate-principal-policy` on instance role for
     `ssmmessages:OpenDataChannel` and on caller role for
     `ssm:StartSession`.
   - VPC endpoints: `ec2 describe-vpc-endpoints` for the three
     required endpoints (ssm, ec2messages, ssmmessages); endpoint
     security group inbound 443; private DNS enabled.
   - Timeout: `describe-security-groups` egress on 443, DNS
     resolution, agent log for `dial tcp: i/o timeout`.
   - Agent version: `describe-instance-information` AgentVersion
     against the 2.3.68 (session), 3.0.196 (port forwarding), 3.1
     (macOS) thresholds.
   - Document: `ssm get-document` schema, `DocumentType: Session`,
     `s3BucketName`, `cloudWatchLogGroupName`.
   - Port forwarding: document name (`AWS-StartPortForwardingSession`
     vs `ToRemoteHost`), target host reachability from the instance.
   - Shell profile: agent log for `SessionTypeHandler` errors;
     `.bashrc`/`.bash_profile` on-instance for `exit`/syntax errors.
   - Audit/Output: `get-bucket-policy` for the session-output
     bucket, role `s3:PutObject` simulation, document
     `s3BucketName`.
   - CloudWatch Logs: document `cloudWatchLogGroupName` and
     `cloudWatchStreamingEnabled`, role `logs:PutLogEvents`
     simulation.
   - Patch baseline: `describe-instance-associations-status` for
     `Running` associations during the failure window.
4. **Verdict** — ROOT_CAUSE_IDENTIFIED (with failing probe that
   matches the symptom) or INSUFFICIENT_DATA (all probes pass;
   escalate to AWS Support with the instance id and session id).

Emits a deterministic diagnostic block per target:

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

## When to invoke

Paste a symptom description and ask any of:

- "SSM instance not showing in the console"
- "Session Manager connection timed out"
- "ssm:StartSession AccessDenied"
- "port forwarding NotSupported"
- "session opens and closes immediately"
- "SSM audit logs not in S3"
- "CloudWatch Logs group empty for SSM"
- "macOS cannot start SSM session"

A bare instance id + any session error verb ("session failing",
"cannot connect", "session timeout") also routes here via the
orchestrator.

## Inputs

- Symptom description: error string, observed behaviour,
  intermittent vs persistent, session id.
- Instance configuration: InstanceId, PlatformName (Linux / macOS /
  Windows), AgentVersion, PingStatus, LastPingDateTime,
  InstanceProfile role.
- For live-account diagnosis: VPC and endpoint context (VPC id,
  endpoint list, private DNS), session document name, target host
  for port forwarding, S3 audit bucket name. The skill uses
  `describe-instance-information`, `describe-sessions`,
  `get-document`, `describe-vpc-endpoints`,
  `describe-security-groups`, `simulate-principal-policy`,
  `describe-log-groups`, `get-bucket-policy`,
  `describe-instance-associations-status`.

## Outputs

- One diagnostic block per target instance/session.
- Layer-specific LAYER value from the enumerated set.
- Evidence section with the failing probe AND passing probes (layers
  ruled out) — never a verdict without positive evidence.
- Specific remediation: agent start, role policy update, VPC
  endpoint creation, document update, shell-profile fix, bucket-
  policy update, or AWS Support escalation.

## Related

- `/aws:pipeline` to enter the full CloudOps pipeline (this skill
  is the Phase 2 Troubleshoot specialist for SSM Session Manager
  failures).
- `/aws:troubleshoot-ssm-association` for SSM State Manager
  association failures (different from Session Manager session
  failures).
- `/aws:audit-ssm-managed-instance` for configuration posture
  audits on the same instance (agent version, patch compliance,
  association status).
- `/aws:troubleshoot-iam-permission` for deeper diagnosis when the
  instance or caller role is denied by an SCP, permissions
  boundary, or session policy.
- `/aws:troubleshoot-vpc-connectivity` for deeper diagnosis when
  the instance cannot reach the SSM endpoints because of routing,
  NACL, or peering issues.
