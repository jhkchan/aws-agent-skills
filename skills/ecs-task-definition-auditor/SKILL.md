---
name: ecs-task-definition-auditor
description: >-
  Audits ECS task definitions for privileged containers, plaintext secrets in
  environment variables (instead of Secrets Manager / SSM), host network mode,
  root-user execution, and missing resource limits (CPU / memory / logging).
  Emits a deterministic verdict (PRIVILEGED | SECRET_LEAK | INSECURE |
  CONFIG_GAP | OK) per task definition with enumerated findings and specific
  remediation. Use when reviewing ECS task definitions, checking container
  privilege escalation exposure, validating secret-handling posture, hardening
  Fargate or EC2 launch-type tasks before production deployment, or auditing
  ECS security controls.
version: 0.1.0
author: Jacky Chan — AWS Community Builder
license: Apache-2.0
compatibility: >-
  Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex,
  Gemini). No AWS CLI required for offline task-definition classification.
  Live-account audits use aws ecs describe-task-definition, aws ecs
  list-task-definitions, and aws ecs list-containers (AWS CLI v2, SSO or
  key-based credentials).
keywords:
  - ECS
  - task definition
  - Fargate
  - EC2 launch type
  - privileged container
  - secret leak
  - environment variables
  - Secrets Manager
  - SSM Parameter Store
  - host network mode
  - awsvpc
  - root user
  - non-root container
  - resource limits
  - CPU limit
  - memory limit
  - readonlyRootFilesystem
  - linux capabilities
  - container security
  - defense in depth
tags: [ecs, compute, security, task-definition, fargate, privileged, secrets, container-hardening, audit]
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: true
  phase: 2
  supports_pipeline: true
  entry_point: false
  family: Compute
  verdict_shape: "PRIVILEGED | SECRET_LEAK | INSECURE | CONFIG_GAP | OK"
  when_to_use: >-
    Reviewing an ECS task definition before production deployment, checking for
    privileged containers, auditing secret-handling posture, validating that
    containers run as non-root, hardening network isolation, verifying resource
    limits are set, or auditing ECS container security controls across an
    account.
  activation_triggers:
    - "audit this ECS task definition"
    - "is my ECS container privileged"
    - "check ECS task for secrets in env vars"
    - "ECS task host network mode"
    - "is my container running as root"
    - "ECS resource limits missing"
    - "harden my Fargate task"
    - "ECS security audit"
  invocation_schema: >-
    Input: either (a) an ECS task definition JSON document (the
    containerDefinitions + networkMode + launch-type metadata), OR (b) a
    task-definition family/ARN for live-account audit. Output: deterministic
    TASK/VERDICT/REASON/FINDINGS/REMEDIATION block per task definition, where
    VERDICT ∈ {PRIVILEGED, SECRET_LEAK, INSECURE, CONFIG_GAP, OK, ERROR}.
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

These behaviors are easy to misjudge without operational ECS experience.
Each changes a verdict if ignored:

- **Omitted `user` defaults to root (UID 0).** Docker's default user is
  `root`. An ECS container definition without the `user` field runs as
  root — full filesystem and capability privileges inside the container.
  Many operators assume "no user specified = least privilege." It is the
  opposite. Treat an absent or empty `user` as `user: root` (INSECURE).

- **`privileged: true` on Fargate is a silent no-op.** Fargate does not
  support privileged mode — the flag is accepted at registration but
  ignored at runtime. A task with `requiresCompatibilities: ["FARGATE"]`
  and `privileged: true` is NOT a PRIVILEGED verdict — the container
  never gets elevated privileges. Classify as CONFIG_GAP (dead
  configuration that signals a misunderstanding of Fargate's security
  model and may mask intent if the task is later re-registered as EC2).

- **`user: "0:0"` and `user: "0:0:0"` are root regardless of trailing
  fields.** ECS/Docker support `uid:gid` and `uid:gid:supplementary-group`
  formats. The first field is the UID. `user: "0"` is root.
  `user: "999"` is non-root. `user: "app"` resolves via the container's
  `/etc/passwd` — verify the image defines that user, otherwise it
  silently falls back to root.

- **`networkMode: host` is rejected at Fargate registration.** You cannot
  register a Fargate task with `networkMode: host` — the API returns
  `ClientException`. If the input shows `requiresCompatibilities:
  ["FARGATE"]` + `networkMode: host`, the definition is invalid —
  classify as ERROR, not INSECUE.

- **`secrets` array values are NEVER in the task definition JSON.** The
  `secrets` array stores only a `name` and a `valueFrom` ARN (Secrets
  Manager or SSM SecureString). The actual secret value is injected at
  container start. This is the correct pattern. Only `environment` values
  are plaintext in the definition. Do NOT flag `secrets` entries as
  leaks — they are the remediation.

- **`memory` (hard limit) vs `memoryReservation` (soft limit).** Docker
  OOM-kills a container that exceeds `memory` (hard). Without a hard
  limit, a single container can consume all host memory, causing the
  host to OOM-kill other tasks or the ECS agent itself. On EC2, the
  absence of container-level `memory` is a real CONFIG_GAP. On Fargate,
  task-level `memory` is the enforced limit — container-level `memory`
  is advisory only.

- **Fargate enforces fixed CPU/memory combinations.** Valid task-level
  CPU: 256 (.25 vCPU), 512 (.5), 1024 (1), 2048 (2), 4096 (4), 8192 (8),
  16384 (16). Memory varies by CPU tier (e.g., 0.25 vCPU allows 512 MB /
  1 GB / 2 GB). Non-matching values are rejected at registration. A task
  registered with a non-standard combination has either been mis-specified
  or the audit input is stale.

- **`readonlyRootFilesystem` defaults to `false`.** Without it, a
  compromised container can write malware to its filesystem, modify
  binaries, and persist credentials. Setting `readonlyRootFilesystem:
  true` forces applications to use `mountPoints`/`volumes` for writes,
  reducing the attack surface. Omission is an INSECURE sub-finding.

- **`initProcessEnabled: true` is a signal-handling requirement, not
  just hygiene.** Without init (tini/dumb-init), PID 1 inside the
  container is your application process. Most applications do not
  properly reap zombie children or handle SIGTERM. ECS sends SIGTERM
  during draining — without init, the container may hang until the
  30-second timeout and then get SIGKILL'd, losing in-flight work.

- **Linux capabilities ADD is a scoped `privileged` alternative.** Docker
  grants ~14 default capabilities. Adding `SYS_ADMIN`, `NET_ADMIN`,
  `SYS_PTRACE`, `SYS_MODULE`, `DAC_READ_SEARCH`, or `SYS_RAWIO` is
  nearly as dangerous as `privileged: true` — each enables a documented
  container-escape or kernel-tampering path. Flag as INSECURE.

- **`dockerSecurityOptions: ["no-new-privileges:true"]` prevents setuid
  escalation.** Without it, a setuid-root binary inside the container
  can escalate to root even if the container runs as non-root. Default
  in Docker is `false` (allows escalation). Setting it `true` is
  defense-in-depth.

- **`enableExecute` (ECS Exec) is a lateral-movement vector.** When
  enabled, anyone with `ssm:StartSession` on the task can open a shell
  in the running container via Session Manager. If the task role is
  over-privileged or the SSM IAM policy is broad, this is a privilege
  escalation path. Flag as a CONFIG_GAP sub-finding.

- **`runtimePlatform.cpuArchitecture` must match the container image.**
  `ARM64` (Graviton) images cannot run on `X86_64` and vice versa. A
  mismatch causes an `exec format error` at runtime. Not a security
  finding, but flag as a CONFIG_GAP if the platform is set without
  verifying image compatibility.

- **Bind mounts from the host are a container-isolation bypass.** The
  `volumes` array with `host: { sourcePath: "/var/run/docker.sock" }`
  grants the container direct access to the Docker daemon socket — it can
  start, stop, and inspect every other container on the host, effectively
  achieving full host compromise without `privileged: true`. Similarly,
  mounting `/`, `/etc`, `/proc`, or `/sys` bypasses all filesystem
  isolation. A bind mount of any host path is an INSECURE finding — treat
  `docker.sock` mounts as equivalent to PRIVILEGED.

- **`systemControls` kernel parameters are NOT isolated on bridge/host
  networking.** `systemControls` sets sysctl values inside the container's
  network namespace. On `awsvpc` mode, network sysctls (`net.*`) are
  isolated per task (each task has its own netns). On `bridge` or `host`
  mode, network sysctls affect the HOST kernel — `net.core.somaxconn` set
  by container A changes the host's listen backlog for all containers. A
  malicious container on bridge mode can use `systemControls` to manipulate
  host networking behavior. Flag `systemControls` with `net.*` keys on
  non-awsvpc tasks as an INSECURE sub-finding.

- **`extraHosts` is a DNS injection vector.** The `extraHosts` field adds
  entries to `/etc/hosts` inside the container. A task definition that
  overrides `metadata.aws.internal` or `169.254.169.254` can redirect IMDS
  calls to an attacker-controlled endpoint, capturing instance credentials.
  Audit `extraHosts` for entries that override well-known AWS or
  infrastructure hostnames.

- **`links` is deprecated but silently enables inter-container
  communication on bridge.** The `links` field (deprecated, bridge-only)
  sets `/etc/hosts` entries and injects link-alias environment variables.
  Critically, linked containers can communicate even when the Docker
  daemon's `icc` (inter-container communication) flag is `false` — links
  are an explicit hole in the bridge isolation. Flag `links` usage as a
  CONFIG_GAP (deprecated, breaks Fargate migration).

- **Fargate platform versions have divergent security feature support.**
  Platform 1.4.0 (current `LATEST`) supports `initProcessEnabled`,
  ephemeral storage API, and `awslogs` exclusively. Platform 1.3.0 does NOT
  support `initProcessEnabled`, does not support `readonlyRootFilesystem`
  reliably, and routes logs through a different agent. Migrating from 1.3.0
  to 1.4.0 silently changes the logging delivery path. If the task
  definition specifies `platformVersion: "1.3.0"`, flag the missing
  security features as a CONFIG_GAP.

- **ECS Exec (`enableExecute`) is a lateral-movement vector.** When enabled
  on the ECS service, anyone with `ssm:StartSession` on the task can open
  a root shell in the running container via Session Manager. The exec
  channel requires (1) `enableExecute: true` on the service, (2) the task
  role having `ssmmessages:CreateControlChannel` / `CreateDataChannel` /
  `OpenControlChannel` / `OpenDataChannel`, and (3) the execution role
  having the same SSM permissions. If the task role is over-privileged
  (e.g., `*` on `ssm:*`), any principal with `sts:AssumeRole` on the task
  role can pivot into every running container of that task. Flag
  `enableExecute` combined with broad task-role SSM permissions as
  INSECURE.

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

- **Multiple containers, mixed privilege.** A task with two containers
  — one privileged, one not — is PRIVILEGED. The verdict reflects the
  worst container. Name the offending container(s) in the FINDINGS.

- **`privileged: true` on Fargate.** Classify as CONFIG_GAP, NOT
  PRIVILEGED. Fargate silently ignores the flag. The container never
  receives elevated privileges. Flag the dead configuration and note
  the intent mismatch.

- **`environment` key that looks like a secret but is a config flag.**
  Keys like `PASSWORD_POLICY_MIN_LENGTH=12` or
  `SECRET_MANAGER_ENABLED=true` match the `PASSWORD` / `SECRET` patterns
  but hold configuration, not credentials. Apply the false-positive
  exclusions (Step 2). When ambiguous, flag as SECRET_LEAK with a note:
  "key name matches secret pattern; verify the value is not a
  credential." False positives on secret detection are preferable to
  false negatives — a missed credential leak is a security incident.

- **Named user that does not exist in the image.** `user: "appuser"`
  where the image has no such user in `/etc/passwd` causes Docker to
  fall back to root at runtime. If the image cannot be inspected, emit
  a note: "named user 'appuser' — verify the image defines this UID;
  otherwise the container silently runs as root." Do NOT classify as
  OK without verification; do NOT classify as INSECUE without proof.

- **Empty `containerDefinitions` array.** A task definition with no
  containers is invalid — ECS requires at least one container. Output
  ERROR.

- **`networkMode: host` on a mixed-compatibility task.** A task with
  `requiresCompatibilities: ["EC2","FARGATE"]` and `networkMode: host`
  is technically registrable (Fargate registration would fail at run
  time). Classify as INSECUE for the EC2 dimension and note the
  Fargate incompatibility.

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

### For PRIVILEGED — privileged container on EC2

1. Set `privileged: false` on the offending container definition.
2. If the container genuinely needs elevated access, add only the
   minimum required capability via `linuxParameters.capabilities.add`.
   Document why each capability is needed.
3. Register a new revision:
   `aws ecs register-task-definition --cli-input-json file://fixed-task-def.json`
4. Update the service:
   `aws ecs update-service --cluster <cluster> --service <service> --task-definition <family:new-revision>`
5. If the privileged container was running untrusted code or was
   internet-reachable, assume host compromise. Replace the EC2 instance
   and audit CloudTrail for anomalous activity during the exposure window.

### For SECRET_LEAK — plaintext secret in environment

1. Move the secret to the `secrets` array:
   ```json
   "secrets": [
     {
       "name": "DATABASE_PASSWORD",
       "valueFrom": "arn:aws:secretsmanager:us-east-1:111111111111:secret:prod/db-password-AbCdEf"
     }
   ]
   ```
2. **Rotate the credential in the backing service** (database password,
   API key, etc.). The plaintext value persists in every historical
   task definition revision and in CloudTrail `RegisterTaskDefinition`
   events.
3. Verify the task role has `secretsmanager:GetSecretValue` (or
   `ssm:GetParameter` with decryption) for the referenced ARN.
4. Register a new revision and update the service.
5. After the new revision is stable, deregister all old revisions that
   contain the plaintext secret.

### For INSECURE — host network mode

1. Change `networkMode` from `host` to `awsvpc` (recommended) or
   `bridge`. `awsvpc` gives each task its own ENI + security group.
2. If switching to `awsvpc`, update the service's security group to
   allow the required inbound ports (previously bound on the host).
3. Update port mappings: `hostPort` is ignored on `awsvpc` (use
   `containerPort` only) or must be 0 on Fargate.

### For INSECURE — root user

1. Set `user` to a non-zero UID: `"user": "1000"` or `"user": "1000:1000"`.
2. Verify the container image creates this user in its Dockerfile
   (`RUN useradd -u 1000 appuser`). A named user that does not exist
   in the image silently falls back to root.
3. Set `readonlyRootFilesystem: true` for defense-in-depth. If the
   application writes temp files, mount a `tmpfs` volume:
   ```json
   "mountPoints": [{"containerPath": "/tmp", "sourceVolume": "tmp"}],
   "volumes": [{"name": "tmp", "host": null}]
   ```

### For INSECURE — dangerous capabilities

1. Remove the dangerous capability from `linuxParameters.capabilities.add`.
2. If the capability is genuinely required, document the justification
   and add compensating controls: `readonlyRootFilesystem: true`,
   `no-new-privileges:true`, and a restrictive AppArmor profile.
3. Prefer `SYS_PTRACE` (scoped) over `SYS_ADMIN` (broad) when choosing
   the minimum viable capability.

### For CONFIG_GAP — missing resource limits

1. Set task-level `cpu` and `memory` (required for Fargate):
   ```json
   "cpu": "512",
   "memory": "1GB"
   ```
2. Set container-level `memory` (hard limit) on each container for EC2
   launch type. Use `memoryReservation` for the soft limit.
3. Verify the values match Fargate's fixed CPU/memory combinations if
   applicable.

### For CONFIG_GAP — missing log configuration

1. Add `logConfiguration` to each container:
   ```json
   "logConfiguration": {
     "logDriver": "awslogs",
     "options": {
       "awslogs-group": "/ecs/<family>",
       "awslogs-region": "us-east-1",
       "awslogs-stream-prefix": "ecs"
     }
   }
   ```
2. Verify the execution role has `logs:CreateLogStream` and
   `logs:PutLogEvents`.

### For CONFIG_GAP — missing execution role

1. Create or reference an execution role with the managed policy
   `AmazonECSTaskExecutionRolePolicy` (covers ECR pull + CloudWatch Logs).
2. Set `executionRoleArn` on the task definition.

### For OK

1. No remediation required for the current posture.
2. Recommend `initProcessEnabled: true` for signal-handling correctness
   (defense-in-depth, not a security verdict driver).
3. Recommend `dockerSecurityOptions: ["no-new-privileges:true"]` to
   prevent setuid escalation.

## Deep reference: ECS security internals

### Launch-type security model comparison

| Dimension | EC2 | Fargate |
|---|---|---|
| `privileged: true` | Full host kernel access | Silently ignored (no-op) |
| `networkMode` | `bridge`, `host`, `awsvpc`, `none` | `awsvpc` only (required) |
| Container `memory` (hard limit) | Enforced by Docker cgroup | Advisory — task-level `memory` is the real limit |
| Container `cpu` | Enforced via CFS quota | Advisory — task-level `cpu` is the real limit |
| `host` port mappings | Supported | Rejected (use `containerPort` only) |
| Linux capabilities | Honored | Honored (scoped subset) |
| `readonlyRootFilesystem` | Honored | Honored |
| Resource isolation | Shared EC2 host (noisy-neighbor risk) | Dedicated micro-VM per task |

### Secret injection lifecycle

ECS injects secrets at container start, not at registration:
1. `RegisterTaskDefinition` stores the `secrets` array (name + ARN only)
   in the task definition JSON. The actual secret value is NEVER stored.
2. At task start, the ECS agent (EC2) or Fargate platform assumes the
   execution role and calls `secretsmanager:GetSecretValue` or
   `ssm:GetParameter` (with decryption) for each referenced secret.
3. The resolved value is injected as an environment variable inside the
   container, visible to the application process but NOT in the task
   definition JSON, CloudTrail, or the ECS console.

This is why `secrets` is safe and `environment` is not — the value
travels a different path entirely.

**Required IAM policy for secret injection.** The execution role (not the
task role) must grant permission to read the referenced secret. Without
this policy, the task fails at start with `ResourceInitializationError`:

```json
{
  "Effect": "Allow",
  "Action": "secretsmanager:GetSecretValue",
  "Resource": "arn:aws:secretsmanager:us-east-1:111111111111:secret:prod/*"
}
```

For SSM SecureString references, substitute
`ssm:GetParameter` + `kms:Decrypt` (for the KMS key used to encrypt the
parameter). A common misconfiguration is granting these to the task role
(application container) instead of the execution role (ECS agent) — the
container never sees the IAM denial because the injection fails before
the container starts.

**Required IAM policy for ECS Exec.** When `enableExecute` is enabled on
the service, both the task role AND execution role need SSM messaging
permissions. The exact required actions are:

```json
{
  "Effect": "Allow",
  "Action": [
    "ssmmessages:CreateControlChannel",
    "ssmmessages:CreateDataChannel",
    "ssmmessages:OpenControlChannel",
    "ssmmessages:OpenDataChannel"
  ],
  "Resource": "*"
}
```

Scope the `Resource` to the task's own ARN when possible. A task role
with `ssm:*` on `*` turns ECS Exec into an open shell-access vector —
any principal who can assume the task role gets a root shell in every
running container.

### Task definition revision immutability

Every `RegisterTaskDefinition` call creates a new immutable revision
(family:N+1). Old revisions are never overwritten — they remain
queryable via `describe-task-definition` until deregistered. This means:
- A plaintext secret in `environment` persists across ALL revisions
  that ever contained it, even after a new revision removes it.
- Deregistering a revision prevents new tasks from using it but does
  NOT delete the JSON — `describe-task-definition` still returns the
  full definition including the plaintext value.
- The only way to fully scrub a leaked credential is to rotate it in
  the backing service. Moving it to `secrets` prevents future leaks
  but does not retroactively protect historical revisions.

### Capability-to-privilege escalation mapping

| Capability | Escape vector |
|---|---|
| `SYS_ADMIN` | Mount host filesystem, manipulate cgroups, create namespaces — full host compromise |
| `NET_ADMIN` | Redirect traffic via iptables, create raw sockets, ARP spoofing on the host network |
| `SYS_PTRACE` | `process_vm_writev` to inject code into host processes via /proc/<pid>/mem |
| `SYS_MODULE` | `init_module` / `finit_module` to load a malicious kernel module — root-equivalent |
| `DAC_READ_SEARCH` | `open_by_handle_at` to read any file on the host filesystem bypassing permissions |
| `SYS_RAWIO` | Direct disk I/O — can read/write raw blocks, bypassing the filesystem layer |

## Recent AWS features (2024-2026)

- **EBS volumes for ECS tasks (2024):** ECS tasks can now mount EBS volumes in addition to EFS. This changes the audit surface — auditors should verify that EBS volumes attached to ECS tasks are encrypted and that the task role has scoped KMS permissions.
- **Fargate EFA support (2024-2025):** AWS Fargate now supports Elastic Fabric Adapter (EFA) for HPC/ML workloads. Auditors should verify that EFA-enabled tasks are placed on instances that support EFA and that the security group allows EFA traffic.
- **Deployment circuit breaker (2024):** ECS deployment circuit breaker automatically rolls back failed deployments. Auditors should verify that the circuit breaker is enabled on production services — without it, a bad deployment stays in place requiring manual intervention.
- **Service Connect (2024):** ECS Service Connect provides built-in service discovery and load balancing. Auditors should verify that Service Connect configurations do not bypass security group controls and that inter-service traffic is properly encrypted.
- **Health check policy (2024-2025):** Enhanced health check policies with graceful shutdown support. Auditors should verify that `deregistrationDelay` and `healthCheckGracePeriod` are tuned for the workload — too short causes premature termination, too long delays rollback.

## Domain

AWS CloudOps / ECS Compute Security & Container Hardening.

## AWS documentation

- **Amazon Elastic Container Service Developer Guide** — https://docs.aws.amazon.com/AmazonECS/latest/developerguide/Welcome.html
- **ECS Security** — https://docs.aws.amazon.com/AmazonECS/latest/developerguide/security.html
- **ECS API Reference** — https://docs.aws.amazon.com/AmazonECS/latest/APIReference/
- **ECS CLI Reference** — https://docs.aws.amazon.com/cli/latest/reference/ecs/
- **Deployment circuit breaker** — https://docs.aws.amazon.com/AmazonECS/latest/developerguide/deployment-circuit-breaker.html
