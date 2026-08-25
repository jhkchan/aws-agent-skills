---
name: ecs-task-definition-auditor
description: Audits ECS task definitions for privileged containers, plaintext secrets in environment variables (instead of Secrets Manager / SSM), host network mode, root-user execution, and missing resource limits (CPU / memory / logging). Emits a deterministic verdict (PRIVILEGED | SECRET_LEAK | INSECURE | CONFIG_GAP | OK) per task definition with enumerated findings and specific remediation. Use when reviewing ECS task definitions, checking container privilege escalation exposure, validating secret-handling posture, hardening Fargate or EC2 launch-type tasks before production deployment, or auditing ECS security controls.
license: Apache-2.0
compatibility: Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). No AWS CLI required for offline task-definition classification. Live-account audits use aws ecs describe-task-definition, aws ecs list-task-definitions, and aws ecs list-containers (AWS CLI v2, SSO or key-based credentials).
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: 'true'
  phase: '2'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: Compute
  verdict_shape: PRIVILEGED | SECRET_LEAK | INSECURE | CONFIG_GAP | OK
  when_to_use: Reviewing an ECS task definition before production deployment, checking for privileged containers, auditing secret-handling posture, validating that containers run as non-root, hardening network isolation, verifying resource limits are set, or auditing ECS container security controls across an account.
  activation_triggers: audit this ECS task definition, is my ECS container privileged, check ECS task for secrets in env vars, ECS task host network mode, is my container running as root, ECS resource limits missing, harden my Fargate task, ECS security audit
  invocation_schema: 'Input: either (a) an ECS task definition JSON document (the containerDefinitions + networkMode + launch-type metadata), OR (b) a task-definition family/ARN for live-account audit. Output: deterministic TASK/VERDICT/REASON/FINDINGS/REMEDIATION block per task definition, where VERDICT ∈ {PRIVILEGED, SECRET_LEAK, INSECURE, CONFIG_GAP, OK, ERROR}.'
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  keywords: ECS, task definition, Fargate, EC2 launch type, privileged container, secret leak, environment variables, Secrets Manager, SSM Parameter Store, host network mode, awsvpc, root user, non-root container, resource limits, CPU limit, memory limit, readonlyRootFilesystem, linux capabilities, container security, defense in depth
  tags: ecs, compute, security, task-definition, fargate, privileged, secrets, container-hardening, audit
---

# ECS Task Definition Auditor

## Mindset

**One-line takeaway:** the verdict is always the **worst** finding across
five ordered dimensions, and the priority is strict —
`PRIVILEGED > SECRET_LEAK > INSECURE > CONFIG_GAP > OK`.

An ECS task definition is the security blueprint for every container that
runs under it. Unlike a Dockerfile (which can be overridden at runtime), a
task definition is the authoritative source for IAM role binding, network
isolation, secret injection, resource limits, and Linux security options.
Three facts make ECS auditing different from generic container scanning:

- **`privileged: true` on EC2 grants full host kernel access** — the
  container bypasses seccomp, AppArmor, capabilities restrictions, and
  device cgroup controls. It is root-equivalent on the underlying host.
- **Omitted `user` defaults to root (UID 0).** Docker's default user is
  `root`. A container definition without `user` does NOT mean "no special
  user" — it means "runs as root." This is the single most common ECS
  misconfiguration.
- **`environment` is plaintext in the task definition JSON.** Unlike
  `secrets` (which store only an ARN reference), every value in
  `environment` is visible via `describe-task-definition`, CloudTrail
  event logs, the ECS console, and the API. A password in `environment`
  is a committed credential leak.

## Quick reference — verdict thresholds

| Condition | Verdict | Step |
|---|---|---|
| `privileged: true` on EC2 launch type | **PRIVILEGED** | Step 1 |
| Secret-pattern key in plaintext `environment` | **SECRET_LEAK** | Step 2 |
| `networkMode: host` | **INSECURE** | Step 3a |
| `user: root` / `user: "0"` / user omitted | **INSECURE** | Step 3b |
| Dangerous Linux capability ADD (`SYS_ADMIN`, `NET_ADMIN`, `SYS_PTRACE`, `SYS_MODULE`) | **INSECURE** | Step 3c |
| `readonlyRootFilesystem: false` or omitted | **INSECURE** (sub-finding) | Step 3d |
| No task-level or container-level `memory` hard limit | **CONFIG_GAP** | Step 4a |
| Missing `logConfiguration` on any container | **CONFIG_GAP** | Step 4b |
| Missing `executionRoleArn` (ECR pull / CloudWatch logs fail) | **CONFIG_GAP** | Step 4c |
| All dimensions pass | **OK** | Step 5 |

See the ordered steps below for edge cases. Deep ECS security internals
(launch-type matrix, Fargate constraints, capability catalog) are in the
[Deep reference](#deep-reference-ecs-security-internals) section at the end.

## Pre-flight: task metadata gate (run before classification)

Before evaluating container definitions, classify the task's launch type and
network mode. Several attributes **short-circuit** the audit —
misclassifying them produces false positives that erode trust.

| Attribute | Value | Effect on audit |
|---|---|---|
| `requiresCompatibilities` | `["FARGATE"]` | **Fargate-only task.** `privileged` is silently ignored (no-op). `networkMode` MUST be `awsvpc` or registration fails. Container-level `cpu`/`memory` are advisory — only task-level values are enforced. `host` port mappings are rejected. |
| `requiresCompatibilities` | `["EC2"]` or absent | **EC2 launch type.** `privileged: true` grants full host access. Container-level `memory` (hard limit) is enforced. `networkMode` can be `bridge`, `host`, `awsvpc`, or `none`. |
| `requiresCompatibilities` | `["EC2","FARGATE"]` | **Mixed compatibility.** Audit for the worst-case (EC2) — `privileged` is live on EC2 even though Fargate ignores it. Flag `host` network mode as an EC2-only constraint that breaks Fargate compatibility. |
| `networkMode` | `awsvpc` | Recommended. Each task gets its own ENI + security group. Required for Fargate. |
| `networkMode` | `host` | **No network namespace isolation.** Container shares the host's network stack — can bind any port, sniff host traffic. Not supported on Fargate. |
| `networkMode` | `bridge` | Docker default NAT. Less isolated than `awsvpc` (containers on same bridge can communicate freely). Acceptable for EC2, not Fargate. |
| `networkMode` | `none` | Loopback only. Most restrictive. Rarely used but safe. |

**If the task definition JSON is malformed** (invalid JSON, missing
`containerDefinitions`, no `family`), output:

```text
TASK: <family-or-unknown>
VERDICT: ERROR
REASON: Task definition is not valid JSON or is missing required fields (containerDefinitions, family) — cannot classify.
REMEDIATION: Retrieve the canonical definition with `aws ecs describe-task-definition --task-def <family> --query taskDefinition --output json` and re-audit.
```

## Process — Classification logic (apply in order, aggregate worst)

### Step 0: Expert knowledge — non-obvious ECS behaviors that change classification

Moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md) - load on demand (see References below).

### Step 1: Privileged mode check (PRIVILEGED)

For each container definition in `containerDefinitions`:

- If `privileged: true` AND launch type is EC2 (or `requiresCompatibilities`
  is absent, includes `EC2`, or includes both `EC2` and `FARGATE`):
  → **PRIVILEGED**. The container bypasses all Docker security isolation
  — seccomp, AppArmor, capabilities restrictions, and device cgroup
  controls. It is root-equivalent on the host. A container-escape is
  trivially achievable.

- If `privileged: true` AND `requiresCompatibilities` is `["FARGATE"]`
  only:
  → **CONFIG_GAP** (not PRIVILEGED). Fargate ignores the flag. The
  container never gets elevated privileges. But the flag signals a
  misunderstanding of Fargate's security model and may mask intent if
  the task is later re-registered with EC2 compatibility. Emit a note.

- If `privileged: false` or omitted: no finding on this dimension.

### Step 2: Secret leak check (SECRET_LEAK)

For each container definition, scan the `environment` array (NOT the
`secrets` array) for keys matching secret-value patterns. A key match
indicates a secret stored in plaintext instead of being injected via
Secrets Manager or SSM SecureString.

**Secret-key detection patterns (case-insensitive substring match on the
key name):**

| Pattern | Examples | Rationale |
|---|---|---|
| `PASSWORD` | `DATABASE_PASSWORD`, `REDIS_PASSWORD`, `DB_PASSWORD` | Credentials for authenticated services |
| `PASSWD` | `MYSQL_PASSWD` | Abbreviated password field |
| `PWD` | `DB_PWD`, `RDS_PWD` | Abbreviated password field |
| `SECRET` | `JWT_SECRET`, `CLIENT_SECRET`, `APP_SECRET` | Symmetric signing keys, OAuth client secrets |
| `TOKEN` | `API_TOKEN`, `AUTH_TOKEN`, `CSRF_TOKEN` | Bearer tokens, API tokens |
| `API_KEY` / `APIKEY` | `STRIPE_API_KEY`, `GOOGLE_APIKEY` | Third-party API credentials |
| `ACCESS_KEY` / `ACCESSKEY` | `AWS_ACCESS_KEY_ID`, `GCP_ACCESS_KEY` | Cloud provider credentials (even the "public" access key ID should be in secrets) |
| `PRIVATE_KEY` / `PRIVATEKEY` | `RSA_PRIVATE_KEY`, `SSH_PRIVATEKEY` | Cryptographic private material |
| `CREDENTIAL` / `CREDENTIALS` | `GITHUB_CREDENTIALS`, `SMTP_CREDENTIALS` | General credential bundles |

**False-positive exclusions** (do NOT flag these as SECRET_LEAK even if
the key contains a pattern):
- `*_URL` / `*_HOST` / `*_PORT` / `*_ENDPOINT` (connection metadata, not
  the secret itself).
- `*_ENABLED` / `*_REQUIRED` / `*_POLICY` / `*_ALGORITHM` / `*_PROVIDER`
  (configuration flags, not secret values).
- `*_KEY_ID` where the key ALSO matches `ACCESS_KEY` — this is a known
  edge case. Flag it: AWS access key IDs are semi-public but should
  still not be in environment variables (use the task role instead).

If any environment key matches a secret pattern:
→ **SECRET_LEAK**. The secret value is permanently committed in the task
definition JSON, visible via `describe-task-definition`, CloudTrail
(`RegisterTaskDefinition` / `UpdateTaskDefinition` events), and the ECS
console. Rotating the secret does NOT scrub historical task definition
revisions — the value persists in every revision until the revision is
deregistered.

### Step 3: Insecure configuration check (INSECURE)

Evaluate three sub-dimensions. Any match produces an INSECURE finding.

**Step 3a: Host network mode**
- `networkMode: host` → **INSECURE** (finding: `HOST_NETWORK`). The
  container shares the host's network namespace — no isolation. The
  container can bind any host port, intercept host traffic, and
  enumerate other services on localhost. Use `awsvpc` (recommended) or
  `bridge` instead.
- `networkMode: awsvpc`, `bridge`, or `none`: no finding.

**Step 3b: Root user**
For each container definition, evaluate the `user` field:
- `user: root` or `user: "root"` → **INSECURE** (finding: `ROOT_USER`).
- `user: "0"` or `user: 0` → **INSECURE** (finding: `ROOT_USER`).
- `user: "0:0"` or `user: "0:0:0"` → **INSECURE** (finding: `ROOT_USER`).
- `user` omitted or empty string → **INSECURE** (finding: `ROOT_USER`).
  Docker's default user is root (UID 0). This is the most common ECS
  misconfiguration.
- `user: "<non-zero-uid>"` (e.g., `"1000"`, `"1000:1000"`) → no finding
  (non-root).
- `user: "app"` or any named user → verify the container image defines
  that user. If unverifiable, emit a note but do NOT flag as INSECUE
  (named users are non-root if they exist).

**Step 3c: Dangerous Linux capabilities**
For each container's `linuxParameters.capabilities.add`, check for
dangerous capabilities:

| Capability | Risk |
|---|---|
| `SYS_ADMIN` | Broad system administration — enables mount, namespace manipulation, cgroup modification. Nearly equivalent to `privileged`. |
| `NET_ADMIN` | Network configuration — can modify iptables, create interfaces, intercept traffic. |
| `SYS_PTRACE` | Process tracing — can read /proc/<pid>/mem of other processes, inject code. |
| `SYS_MODULE` | Load/unload kernel modules — full kernel compromise. |
| `DAC_READ_SEARCH` | Bypasses file permission checks — read any file on the host. |
| `SYS_RAWIO` | Direct I/O access — can read/write disk blocks bypassing the filesystem. |

If any dangerous capability is ADDed → **INSECURE** (finding:
`DANGEROUS_CAPABILITY`).

**Step 3d: Writeable root filesystem**
- `readonlyRootFilesystem: false` or omitted → INSECURE sub-finding
  (finding: `WRITEABLE_ROOTFS`). Not a standalone INSECURE verdict
  driver — append to an existing INSECURE finding or upgrade a CONFIG_GAP
  to INSECURE if this is the only insecure-flag sub-dimension present.

### Step 4: Config gap check (CONFIG_GAP)

Evaluate operational hardening gaps that do not grant direct attack
surface but indicate missing production-readiness controls.

**Step 4a: Missing resource limits**
- No task-level `memory` AND no container-level `memory` on any
  container → **CONFIG_GAP** (finding: `NO_MEMORY_LIMIT`). Without a
  hard memory limit, a container can consume all host memory, causing
  the host to OOM.
- No task-level `cpu` AND no container-level `cpu` → **CONFIG_GAP**
  (finding: `NO_CPU_LIMIT`). On EC2, the container gets an unbounded
  CPU share. On Fargate, the API requires task-level `cpu` — if absent,
  registration would have failed.
- Container has `memoryReservation` (soft limit) but no `memory` (hard
  limit) → **CONFIG_GAP** (finding: `NO_HARD_MEMORY_LIMIT`). The soft
  limit is a hint; the hard limit is what prevents OOM.

**Step 4b: Missing log configuration**
- Any container without `logConfiguration` → **CONFIG_GAP** (finding:
  `NO_LOGGING`). Container stdout/stderr is lost on task exit. Without
  logs, debugging failures and security forensics are impossible. The
  standard driver for ECS is `awslogs` (CloudWatch Logs).

**Step 4c: Missing execution role**
- No `executionRoleArn` → **CONFIG_GAP** (finding:
  `MISSING_EXECUTION_ROLE`). The ECS agent uses this role to pull the
  container image (ECR) and write logs (CloudWatch). Without it, the
  task fails to start if the image is in ECR or if `awslogs` logging is
  configured. Not a security risk per se, but a guaranteed operational
  failure.

**Step 4d: Missing health check**
- Essential container without `healthCheck` → **CONFIG_GAP** sub-finding
  (finding: `NO_HEALTH_CHECK`). Without a health check, ECS cannot
  detect application-level degradation — the container stays RUNNING
  even if the app is hung. Not a standalone CONFIG_GAP driver; append
  as a sub-finding.

### Step 5: Aggregation — worst verdict wins

The final verdict is the **maximum severity** across all findings, where
PRIVILEGED > SECRET_LEAK > INSECURE > CONFIG_GAP > OK:

```text
verdict = max(all_finding_verdicts)
```

If no findings (all dimensions pass), the verdict is **OK**.

## Output format (per task definition)

```text
TASK: <family:revision>
VERDICT: PRIVILEGED | SECRET_LEAK | INSECURE | CONFIG_GAP | OK
REASON: <1-2 sentences citing the worst finding and step>
FINDINGS:
  - [PRIVILEGED] <finding description (Step N)>
  - [CONFIG_GAP] <finding description (Step N)>
REMEDIATION: <specific action per finding, or "None required" if OK>
```

### Worked example — privileged container with secret leak and no limits

```text
TASK: legacy-app:3
VERDICT: PRIVILEGED
REASON: Container "app" has privileged: true on an EC2 launch type — full
host kernel access (Step 1). Additionally, DATABASE_PASSWORD is stored in
plaintext environment and no memory limit is set.
FINDINGS:
  - [PRIVILEGED] Container "app" has privileged: true on EC2 (Step 1)
  - [SECRET_LEAK] DATABASE_PASSWORD found in plaintext environment (Step 2)
  - [CONFIG_GAP] No task-level or container-level memory hard limit (Step 4a)
REMEDIATION:
  1. Set privileged: false. If kernel-level access is required, use scoped
     linuxParameters.capabilities.add with the minimum needed capability.
  2. Move DATABASE_PASSWORD to the secrets array referencing a Secrets
     Manager ARN. Rotate the leaked value.
  3. Set task-level memory or container-level memory (hard limit).
```

## Edge-case handling

Moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md) - load on demand (see References below).

## Anti-Patterns — NEVER

- NEVER classify `privileged: true` on an EC2 launch type as anything
  other than PRIVILEGED. On EC2, privileged grants ALL Linux
  capabilities, bypasses seccomp/AppArmor, and removes device cgroup
  restrictions. It is root-equivalent on the host. This is not "elevated
  access" — it is total host compromise.

- NEVER treat an omitted `user` field as safe. Docker's default user is
  root (UID 0). A container without `user` runs as root. This is the
  most common ECS misconfiguration and the most common false-negative
  in container security scanning.

- NEVER flag `secrets` array entries as leaks. The `secrets` array
  stores only a `name` and a `valueFrom` ARN — the actual value is
  injected at runtime from Secrets Manager or SSM SecureString. This
  is the correct pattern. Flagging it as a leak is a false positive
  that undermines the skill's credibility.

- NEVER classify `privileged: true` on Fargate as PRIVILEGED. Fargate
  ignores the flag — the container never receives elevated privileges.
  Classifying it as PRIVILEGED conflates "intent to escalate" with
  "actual escalation" and produces false positives.

- NEVER recommend removing all resource limits as a quick fix for noisy
  container restarts. Without a hard `memory` limit, a single
  container can OOM the entire host, killing co-located tasks and the
  ECS agent. The fix for restart loops is to right-size the limit, not
  remove it.

- NEVER assume `networkMode: bridge` is equivalent to `awsvpc` for
  security. Bridge mode allows unrestricted container-to-container
  communication on the same bridge network. `awsvpc` gives each task
  its own ENI and security group — use it when network isolation
  matters.

- NEVER recommend `privileged: true` as a fix for missing capabilities.
  If a container needs a specific capability (e.g., `SYS_PTRACE` for
  debugging), add that single capability via `linuxParameters` — do
  not grant all capabilities. `privileged` is never the least-
  privilege solution.

- NEVER classify a task definition as OK without checking ALL five
  dimensions. A task that is non-privileged and non-root but has a
  plaintext secret in `environment` is SECRET_LEAK, not OK. Skipping
  a dimension because earlier ones passed is the most common audit
  failure.

- NEVER treat `readonlyRootFilesystem: false` as acceptable by default.
  The default is false, which means the container can write anywhere
  in its root filesystem. Setting it true is defense-in-depth that
  prevents malware persistence, binary tampering, and credential
  exfiltration via filesystem writes. Flag as an INSECURE sub-finding.

- NEVER overlook dangerous capabilities in `linuxParameters.capabilities.add`.
  `SYS_ADMIN`, `NET_ADMIN`, `SYS_PTRACE`, `SYS_MODULE`,
  `DAC_READ_SEARCH`, and `SYS_RAWIO` each enable documented container-
  escape or kernel-compromise paths. Adding any of these is an INSECURE
  finding, not a CONFIG_GAP.

- NEVER assume a named user (`user: "app"`) is non-root without
  verifying the image defines that user. Docker silently falls back to
  root when the named user does not exist in `/etc/passwd`. Emit a
  verification note rather than a clean bill of health.

- NEVER recommend storing secrets in SSM Parameter Store `String`
  (non-SecureString) type as remediation for a SECRET_LEAK. Only SSM
  `SecureString` (KMS-encrypted) or Secrets Manager are acceptable.
  Plain `String` parameters are readable by anyone with
  `ssm:GetParameter` and are not encrypted at rest.

- NEVER treat a bind mount of `/var/run/docker.sock` as less dangerous
  than `privileged: true`. The Docker socket grants full control of the
  Docker daemon — starting privileged containers, reading every other
  container's filesystem, and escalating to host root. Treat any host
  path mount of docker.sock, `/`, `/proc`, `/sys`, or `/etc` as an
  INSECURE finding at minimum (docker.sock as PRIVILEGED-equivalent).

- NEVER enable ECS Exec (`enableExecute`) without scoping the task role's
  SSM permissions to the minimum required actions
  (`ssmmessages:CreateControlChannel`, `CreateDataChannel`,
  `OpenControlChannel`, `OpenDataChannel`). A task role with `ssm:*` or
  `*` on all resources turns ECS Exec into a lateral-movement vector —
  any principal who can assume the task role gets a shell in every
  running container of that task.

- NEVER move a secret to the `secrets` array without verifying the
  execution role has `secretsmanager:GetSecretValue` (or
  `ssm:GetParameter` + `kms:Decrypt`) on the referenced ARN. A task with
  the correct `secrets` reference but missing IAM permissions fails at
  start with `ResourceInitializationError: unable to retrieve secrets` —
  the remediation for SECRET_LEAK is incomplete without the IAM policy
  update.

- NEVER classify a named user (`user: "appuser"`) as definitively safe
  without noting that Docker falls back to root when the named user is
  absent from the image's `/etc/passwd`. The only way to confirm non-root
  execution is to verify the UID at runtime (`id -u` inside the container
  returns non-zero). Always emit a verification note for named users.

## Pre-flight safety checks (run before any remediation CLI)

- **MANDATORY CONFIRMATION GATE.** Before any state-changing operation
  (`RegisterTaskDefinition`, `UpdateService`, `DeregisterTaskDefinition`),
  the auditor MUST emit:
  `CONFIRM: About to <action> on task definition <family:revision> in
  account <account>. This affects <consequence>. Proceed? (yes/no)`
  Do NOT execute the CLI command until the operator confirms. A new
  task definition revision changes what every running service using
  that family deploys on the next rollout.

- **Capture the current task definition for rollback:**
  `aws ecs describe-task-definition --task-def <family:revision> --query taskDefinition --output json > /tmp/<family>-backup-$(date +%s).json`
  BEFORE any modification. Task definition revisions are immutable but
  the ACTIVE revision pointer is not — rolling back requires re-
  registering the old revision's JSON.

- **Verify the replacement task role and execution role exist** before
  emitting a remediation `RegisterTaskDefinition` command. A task
  definition referencing a deleted role fails at start time with
  `InvalidParameterException`.

- **Prefer registering a NEW revision over deregistering the current
  one.** `DeregisterTaskDefinition` does not affect running tasks but
  prevents new tasks from using that revision. The safe sequence is:
  (1) register a new revision with the fix, (2) update the service to
  use the new revision, (3) wait for the deployment to stabilize,
  (4) then deregister the old revision if cleanup is desired.

- **Secret rotation is mandatory after a SECRET_LEAK finding.** Moving
  the secret to the `secrets` array does not scrub it from historical
  task definition revisions — every revision ever registered with the
  plaintext value still contains it via `describe-task-definition`.
  Rotate the credential in the backing service, then update all
  consumers.

- **For PRIVILEGED findings on EC2,** treat as incident-response. A
  privileged container can have already escaped to the host. Audit
  CloudTrail for anomalous host-level activity and consider replacing
  the underlying EC2 instance.

## Remediation guidance

**Remediation ordering principle:** always prefer registering a new
revision over mutating the current one. Task definition revisions are
immutable — the fix is always "register a new revision with the corrected
JSON, then update the service to point at it." This preserves the audit
trail and enables rollback.

Moved verbatim to [references/remediation.md](references/remediation.md) - load on demand (see References below).

## Deep reference: ECS security internals

Moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md) - load on demand (see References below).

## Recent AWS features (2024-2026)

Moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md) - load on demand (see References below).

## References (load on demand)

- [references/advanced-patterns.md](references/advanced-patterns.md) — Step 0 expert-knowledge catalogue, edge-case handling, the ECS security internals deep reference, and 2024-2026 feature notes, moved verbatim from SKILL.md
- [references/remediation.md](references/remediation.md) — per-verdict remediation recipes (PRIVILEGED, SECRET_LEAK, INSECURE, CONFIG_GAP, OK), moved verbatim from SKILL.md

## Domain

AWS CloudOps / ECS Compute Security & Container Hardening.

## AWS documentation

- **Amazon Elastic Container Service Developer Guide** — https://docs.aws.amazon.com/AmazonECS/latest/developerguide/Welcome.html
- **ECS Security** — https://docs.aws.amazon.com/AmazonECS/latest/developerguide/security.html
- **ECS API Reference** — https://docs.aws.amazon.com/AmazonECS/latest/APIReference/
- **ECS CLI Reference** — https://docs.aws.amazon.com/cli/latest/reference/ecs/
- **Deployment circuit breaker** — https://docs.aws.amazon.com/AmazonECS/latest/developerguide/deployment-circuit-breaker.html
