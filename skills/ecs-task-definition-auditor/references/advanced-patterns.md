# Advanced Patterns (load on demand) — ECS Task Definition Auditor

Step 0 expert-knowledge catalogue, edge-case handling, the ECS security internals deep reference, and 2024-2026 feature notes, moved verbatim from SKILL.md.

---

## Step 0: Expert knowledge — non-obvious ECS behaviors that change classification (moved from SKILL.md)

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

## Edge-case handling (moved from SKILL.md)

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

## Deep reference: ECS security internals (moved from SKILL.md)

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

## Recent AWS features (2024-2026) (moved from SKILL.md)

- **EBS volumes for ECS tasks (2024):** ECS tasks can now mount EBS volumes in addition to EFS. This changes the audit surface — auditors should verify that EBS volumes attached to ECS tasks are encrypted and that the task role has scoped KMS permissions.
- **Fargate EFA support (2024-2025):** AWS Fargate now supports Elastic Fabric Adapter (EFA) for HPC/ML workloads. Auditors should verify that EFA-enabled tasks are placed on instances that support EFA and that the security group allows EFA traffic.
- **Deployment circuit breaker (2024):** ECS deployment circuit breaker automatically rolls back failed deployments. Auditors should verify that the circuit breaker is enabled on production services — without it, a bad deployment stays in place requiring manual intervention.
- **Service Connect (2024):** ECS Service Connect provides built-in service discovery and load balancing. Auditors should verify that Service Connect configurations do not bypass security group controls and that inter-service traffic is properly encrypted.
- **Health check policy (2024-2025):** Enhanced health check policies with graceful shutdown support. Auditors should verify that `deregistrationDelay` and `healthCheckGracePeriod` are tuned for the workload — too short causes premature termination, too long delays rollback.

