---
description: Diagnose AWS Systems Manager (SSM) Session Manager failures via a 7-symptom decision tree and 4-layer health check.
nl_triggers:
  - "Session Manager fails"
  - "session fails to start"
  - "TargetNotConnected"
  - "target instance not reachable"
  - "session-manager-plugin not found"
  - "port forwarding fails"
  - "shell access fails"
  - "SSM session disconnects"
  - "session drops"
  - "IdleDisconnectTimeout"
  - "ssm:StartSession denied"
  - "ssm-sessionmanager-console-perm"
  - "ssmmessages endpoint missing"
  - "SSM agent version too old"
  - "Session Manager key pair"
  - "cross-account session"
  - "start-session error"
  - "port forwarding bind failed"
  - "session terminated ConnectionLost"
routes_to: ssm-session-manager-troubleshooter
---

# /aws:troubleshoot-ssm-session-manager

Activate the `ssm-session-manager-troubleshooter` skill and diagnose
an SSM Session Manager failure via a systematic 7-symptom decision
tree and 4-layer health check (client, IAM, connectivity, agent).

## What it does

Reads an instance-id or target-id and observed symptom, then applies
an 8-step diagnostic process:

1. Run the 4-layer Session Manager health check (client, IAM,
   connectivity, agent).
2. Diagnose target instance not reachable (agent not running,
   not managed, wrong region, hybrid activation expired).
3. Diagnose session fails to start (caller lacks `ssm:StartSession`,
   console user lacks `ssm-sessionmanager-console-perm`, plugin
   missing, KMS key policy).
4. Diagnose port forwarding fails (local port in use, SSH config
   conflict, document scope, malformed parameters).
5. Diagnose shell access fails (agent < 2.3.12.0, shell not
   configured, ssm-user missing, disk full).
6. Diagnose VPC connectivity issues (`ssmmessages.` endpoint
   missing, SG blocks 443, private DNS disabled).
7. Diagnose session disconnects (idle timeout, NAT gateway 350s,
   agent crash, credential expiry).
8. Diagnose latest-feature issues (key pair SSH-over-SSM,
   cross-account KMS key policy and trust).

Emits a deterministic VERDICT per diagnosis:

```text
DIAGNOSIS: <reference>
INSTANCE: <instance-id or target-id>
SESSION: <session-id or "none - not started">
SYMPTOM: TargetNotReachable | SessionFailsToStart | PortForwardingFails | ShellAccessFails | VpcConnectivity | SessionDisconnects | LatestFeature
ROOT_CAUSE: <specific cause cited>
EVIDENCE: <diagnostic signals>
LAYER_CHECK: Client / IAM / Connectivity / Agent
FIX: <action with CLI snippet>
VERIFICATION: <command to confirm fix>
VERDICT: ROOT_CAUSE_FOUND | NEED_MORE_INFO | ESCALATE
NEXT_STEP: <if NEED_MORE_INFO, the next diagnostic>
ESCALATION_PATH: <if ESCALATE, the recommended path>
```

## When to invoke

Paste an instance-id and symptom, or live diagnostic output,
and ask any of:

- "why won't my Session Manager session start"
- "ssm start-session returns TargetNotConnected"
- "the console Start session button is greyed out"
- "my port forwarding tunnel won't bind"
- "sessions drop after a few minutes"
- "shell access returns 'not configured'"
- "cross-account session fails on kms:GenerateDataKey"
- "session disconnects at 5m50s every time"

A bare "instance-id + symptom" also routes here via the
orchestrator.

## Inputs

- Instance-id or target-id (or `mi-*` for hybrid).
- Observed symptom (target-not-reachable / session-fails-to-start /
  port-forwarding-fails / shell-access-fails / vpc-connectivity /
  session-disconnects / latest-feature).
- Region.
- Caller identity ARN (optional, speeds IAM-layer diagnosis).
- Session-id (optional, for mid-session disconnect diagnosis).
- Recent CLI output from `describe-sessions`,
  `describe-instance-information`, `get-connection-status`, etc.
  (optional, speeds diagnosis).
- session-manager-plugin version (optional, client-layer check).
- SSM agent log excerpt (optional, for agent-side session errors).

## Outputs

- One DIAGNOSIS block per session with SYMPTOM, ROOT_CAUSE,
  EVIDENCE, LAYER_CHECK, FIX, VERIFICATION, VERDICT, NEXT_STEP,
  and ESCALATION_PATH fields.
- For ROOT_CAUSE_FOUND: a specific cause + actionable fix CLI.
- For NEED_MORE_INFO: the specific next diagnostic to run (with
  the exact command).
- For ESCALATE: the escalation path (AWS Support, target-account
  key admin, on-prem operator) with the information to include.
- The 4-layer Session Manager health check result for every
  diagnosis.

## Related

- `/aws:pipeline` to enter the full CloudOps pipeline (this skill
  is the Phase 2 Troubleshoot specialist for Management/Session
  Manager).
- `/aws:audit-ssm-managed-instance` for fleet-wide SSM posture
  audit (companion to this skill's per-session focus).
- `/aws:troubleshoot-ssm-association` for association failures
  (Run Command / patch / inventory) rather than session failures.
