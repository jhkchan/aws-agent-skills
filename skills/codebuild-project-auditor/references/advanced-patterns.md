# Advanced Patterns (load on demand) — CodeBuild Project Auditor

Expert-knowledge deep dives, edge-case catalogs, and recent-feature notes moved verbatim from SKILL.md. Load on demand.

---

## Mindset — the four facts (moved from SKILL.md)

A CodeBuild project is the privileged execution surface for everything your
CI/CD pipeline can touch — source credentials, build secrets, artifact
buckets, deployment roles, and the host the build runs on. Four facts make
CodeBuild auditing different from generic container scanning:

- **`privilegedMode: true` flips the build host into a Docker-in-Docker
  container with full kernel capability.** The build container runs with
  `--privileged`; seccomp, AppArmor, device-cgroup isolation are all
  disabled. It is root-equivalent on the underlying build host. CodeBuild
  fleets isolate builds per-project, but a privileged container can still
  mount the host's Docker socket, escape into sibling containers, and read
  the EFS mounts of other builds if file-system locations are misconfigured.
- **`environment.environmentVariables` with `type: PLAINTEXT` (or omitted)
  is committed in cleartext to the project config.** Every value is visible
  via `batch-get-projects`, CloudTrail event logs, the CodeBuild console,
  and the API. A DB password in a plaintext variable is a leaked credential
  regardless of who has access to the build. The correct channel is
  `environment.secretsManager` (ARN reference, fetched at build time) or
  `environmentVariables` with `type: PARAMETER_STORE` / `SECRETS_MANAGER`.
- **`s3LogsConfig.encryptionDisabled: true` is an explicit opt-OUT of
  SSE-KMS for build logs.** S3 default SSE-S3 (AES-256) still applies, but
  customer-managed key material is gone — meaning the logs are unauditable
  via KMS grant tracing and cannot be revoked by key policy. The same field
  on `artifacts` disables SSE-KMS on build output.
- **The CodeBuild service role is assumed by
  `codebuild.amazonaws.com`.** Whatever permissions it carries execute
  during EVERY build — including `buildspec` commands that may come from a
  pull request. An over-permissive role is a privilege-escalation launch
  pad: any contributor who can modify the buildspec can pivot into the
  role's permissions.

## Step 0 — expert knowledge: non-obvious CodeBuild behaviors (moved from SKILL.md)

- **`privilegedMode: true` is REQUIRED for Docker-in-Docker builds** (e.g.,
  building a Docker image inside a CodeBuild container). Without it,
  `docker build` fails with `Cannot connect to the Docker daemon`. This
  means a Docker-build project with `privilegedMode: true` is NOT
  misconfigured — it is the documented way to run DinD. The audit must
  check the buildspec for `docker build` / `docker push` usage before
  flagging privilegedMode. If the buildspec is unavailable, the rule is:
  privilegedMode + non-Docker image (no `docker` in buildspec) = PRIVILEGED.
- **`environment.environmentVariables[].type` defaults to `PLAINTEXT`
  when omitted.** A variable entry like `{"name": "FOO", "value": "bar"}`
  is plaintext — the absence of `type` does not mean "secure default". The
  secure types are `PARAMETER_STORE` and `SECRETS_MANAGER`; both store only
  a parameter/secret ARN reference in the project config, and the value is
  fetched at build time. An auditor that ignores the `type` field will
  miss every plaintext leak.
- **`environment.secretsManager` is a separate array from
  `environmentVariables`.** The `secretsManager` entries use a different
  shape: `{secretsManagerArn, name, type: SECRETS_MANAGER}`. They are
  ALWAYS reference-based (the secret value never appears in the project
  config). Do not flag them as plaintext leaks.
- **`s3LogsConfig.encryptionDisabled: true` does NOT disable SSE-S3** —
  S3 default encryption still applies (AES-256). It disables SSE-KMS
  specifically, meaning the logs lose customer-managed key traceability
  and grant-based revocation. The verdict is NO_ENCRYPTION because the
  *intentional* encryption posture (KMS) is gone, not because the logs
  are literally plaintext-on-disk.
- **`artifacts.encryptionDisabled: true` was historically the only way to
  share artifacts cross-account** (before CodeBuild supported KMS key
  policies in 2019). Some legacy projects still use it. The remediation
  is NOT to flip the flag — it is to use a customer-managed KMS key with
  a key policy that grants the cross-account principal `kms:Decrypt`.
- **CodeBuild service-role trust policies are wildcards by default when
  created via the console.** The console-generated trust policy is
  `Principal: {Service: "codebuild.amazonaws.com"}` with no condition.
  Any CodeBuild project in the account can assume the role — a confused-
  deputy vector. The fix is `aws:SourceArn` scoped to the specific
  project ARN.
- **`iam:PassRole` in the service role is the privilege-escalation
  launchpad.** A buildspec that runs `aws deploy create-deployment
  --service-role-arn arn:aws:iam::...:role/CodeDeployProductionRole`
  passes whatever role the build role is allowed to pass. If the build
  role has `iam:PassRole` on `"*"`, a malicious PR can pivot into any
  deployment role in the account.
- **`source.auth.resource` holds a CODEBUILD-generated credential ARN for
  GitHub/Bitbucket personal-access-token source providers.** The token
  itself is NOT in the project config — CodeBuild stores it server-side
  via `import-source-credentials` and the project references it by ARN.
  Treat the credential ARN as sensitive metadata: anyone who can run
  `list-source-credentials` can revoke or pivot the token. If the project
  uses `source.type: GITHUB` with no `auth` block, the project relies on
  the account-level default credential — a shared token whose revocation
  breaks every project using it. Surface the credential ARN in FINDINGS
  so the operator can audit which projects share the token.
- **ECR image scanning on the build OUTPUT image is NOT a CodeBuild
  setting** — it is an ECR repository property
  (`scanOnPush: true`). A CodeBuild project that builds and pushes a
  Docker image to an ECR repo with `scanOnPush: false` produces
  unscanned artifacts that downstream services deploy blindly. This is
  a Step 7e finding, not a verdict driver; the auditor emits it as a
  NOTE when `environment.image` ends with `-dind` or the buildspec runs
  `docker push`.
- **`source.buildspec` inline vs. `buildspec.yml` in source.** When
  `source.buildspec` is set (inline), the buildspec is part of the project
  config and visible via `batch-get-projects`. When it is in the source
  repo (`buildspec.yml`), a malicious PR can modify it — and the build
  runs with the service role's permissions. If the project uses
  `source.buildspec: <inline>`, that is more deterministic (PR cannot
  change the buildspec).
- **`fileSystemLocations` mounts EFS into the build.** If the EFS is in a
  different account or has a permissive filesystem policy, the build can
  read/write cross-account data. Treat any EFS mount as an INSECURE
  sub-finding unless the filesystem policy is account-scoped.
- **`projectVisibility: PUBLIC_READ` is a real, documented setting** (for
  shared build fleets). It makes the project startable by any AWS
  principal. Treat as CRITICAL — separate verdict surface
  (`VISIBILITY_PUBLIC`) and quarantine.
- **`webhook` with `buildStatusConfig.enabled: true` reports build
  outcomes to GitHub/Bitbucket.** This is generally safe, but if the
  webhook scope includes the build status of privileged branches (e.g.,
  `prod`), it leaks CI status to anyone with read access to the repo.
- **S3 cache buckets (`cache.s3`) inherit the CodeBuild service role's
  permissions.** If the role has `s3:GetObject` on `"*"`, the cache can be
  poisoned by an attacker who can write to any bucket the role reads.
- **The CodeBuild fleet runs Linux containers on EC2 hosts with Nitro
  isolation.** Privileged mode does NOT bypass Nitro (hypervisor-level
  isolation is intact), but it does bypass container-level isolation
  (seccomp, capabilities, device cgroups). The blast radius is the
  container, not the host — but the container has access to the Docker
  socket, so it can start sibling containers with arbitrary mounts.
- **`queuedRetry` and `concurrentBuildLimit` are operational, not
  security.** Do not flag them.
- **CodeBuild project configs are NOT versioned.** `update-project` is a
  destructive in-place replace; there is no rollback. Always snapshot
  before remediation.
- **`environment.imagePullCredentialsType: CODEBUILD` vs
  `SERVICE_ROLE`.** `CODEBUILD` uses the CodeBuild-managed ECR credential
  (works only for AWS-managed images). `SERVICE_ROLE` uses the service
  role's ECR permissions — required for custom ECR images. If the role
  has `ecr:*` on `"*"`, the build can pull any private ECR image in the
  account.
- **`aws codebuild update-project` is a FULL-REPLACE on `--environment`,
  `--artifacts`, `--logs-config`, `--vpc-config`, and `--source`.** There
  are NO field-level toggles like `--no-privileged-mode` or
  `--secrets-manager-arn`; you must pass the COMPLETE environment JSON
  with every field (image, computeType, privilegedMode,
  environmentVariables, secretsManager). Omitting a field in the update
  payload RESETS it to default. The only top-level boolean toggles are
  `--badge-enabled` / `--no-badge-enabled` and `--encryption-key` (the
  artifact-encryption KMS key ARN). This partial-update gotcha is the
  single most common cause of broken remediations — operators run
  `update-project` to flip privilegedMode and accidentally wipe the
  environmentVariables array. Always snapshot first (see Pre-flight) and
  pass the complete JSON structure.

## Edge-case handling (moved from SKILL.md)

- **Partially malformed project config.** If the project JSON parses but
  individual fields are missing (`environment`, `source`, `serviceRole`),
  classify each valid dimension and emit an ERROR note for each missing
  dimension: "Dimension <X> skipped — required field <Y> missing." Do NOT
  silently classify the entire project as ERROR when only one dimension
  is broken.
- **Inline buildspec vs. source buildspec ambiguity.** When
  `source.buildspec` is the literal string `batch/buildspec.yaml` (a
  filename reference, not inline YAML), it is a source-repo buildspec,
  NOT inline. Treat as "buildspec comes from source."
- **Multiple `environment.environmentVariables` with the same name.**
  Later entries overwrite earlier ones. The plaintext-leak check applies
  to the final resolved value.
- **Cross-account service role.** If the serviceRoleArn references a role
  in a different account, treat as an OVERPERMISSIVE_ROLE finding
  (cross-account role assumption is a confused-deputy vector).
- **Resource not provisioned.** If `s3LogsConfig.status: ENABLED` but
  `location` is empty, the project config is broken — CodeBuild cannot
  write logs. Note as ERROR sub-finding; do NOT classify as NO_ENCRYPTION
  (no logs are being written at all).
- **`projectVisibility: PUBLIC_READ`.** Output the verdict for the next-
  worst finding, AND emit a separate `VISIBILITY_PUBLIC` note above the
  verdict block. The PUBLIC_READ setting is not one of the six verdicts
  by design — it is an extraordinary condition that requires human
  quarantine, not a CLI remediation.

## Deep reference — CodeBuild internals (moved from SKILL.md)

### Build-host isolation

CodeBuild runs each build in an isolated EC2 instance backed by the Nitro
hypervisor. Builds from different projects/accounts do NOT share hosts.
However, `privilegedMode: true` bypasses container-level isolation
(seccomp, capabilities, device cgroups) — the container can interact with
the Docker socket, start sibling containers, and mount arbitrary paths.
Nitro hypervisor isolation remains intact (the host kernel is not
directly exposed), but the container-escape surface is wider than a
non-privileged container.

### Secrets-resolution pipeline

At build start, CodeBuild resolves `environment.secretsManager` and
`environmentVariables[type=PARAMETER_STORE|SECRETS_MANAGER]` to actual
values and injects them into the build container as environment
variables. The resolved values appear in the build's `/tmp/env` file
(which is what buildspec commands read). The project config stores only
the ARN reference — the secret value is never committed to the project
config. This is why `type: SECRETS_MANAGER` entries are NOT plaintext
leaks even though they appear in the `environmentVariables` array.

### Fleet multi-tenancy

CodeBuild operates shared managed fleets per region (`BUILD_GENERAL1_*`
compute types). Your build may run on hardware that recently ran another
account's build. Cross-account data leakage is mitigated by per-build
EBS volume wiping, but `cache.type: LOCAL` persists data on the instance
between builds of the SAME project. Do NOT store secrets in the local
cache.

### Project config versioning

CodeBuild project configs are NOT versioned. `update-project` is a
destructive in-place replace. `batch-get-projects` always returns the
current state. There is no audit log of past configs beyond CloudTrail
`UpdateProject` events (which contain the full new config). For rollback,
snapshot to a file before any change.

### Webhook scope

`webhook.filterGroups` determine which Git events trigger builds. A
`HEAD_REF` filter of `refs/heads/prod` triggers on prod pushes — these
builds run with the service role's permissions. If the role is
over-permissive, a malicious PR merged to prod executes with elevated
permissions. Scope webhooks to non-privileged branches and use a
separate project (with a narrower role) for production builds.

### Build badge URL structure

The badge URL is
`https://codebuild.<region>.amazonaws.com/badges/api/v1/project/<hash>/branch/<branch>/status.svg`.
The `<hash>` is derived from the project name and account — it is NOT a
cryptographic secret. Anyone who has seen the badge URL (e.g., embedded
in a README) can fetch the latest build status indefinitely. Revoking
access requires disabling the badge (`badgeEnabled: false`), which
breaks any embedded references.

## Recent AWS features (2024-2026) (moved from SKILL.md)

- **macOS build environments (2024):** CodeBuild now supports macOS (mac1) fleet instances for iOS/macOS application builds. Auditors should note that macOS fleets have different networking and IAM considerations — they run on dedicated hardware and may have different VPC attachment behavior.
- **GitLab integration (2024):** CodeBuild can now use GitLab as a source provider via CodeStar Connections. Auditors should verify that the connection ARN is scoped appropriately and that the source credential does not use long-lived tokens.
- **Lambda compute for builds (2024-2025):** CodeBuild now supports Lambda-based builds for lightweight, fast execution. This changes the audit surface for VPC networking — Lambda-based builds use VPC configuration differently from EC2-based builds.
- **Fleet VPC support (2024):** CodeBuild fleets now support VPC attachment. Auditors should verify that builds accessing private resources have fleet VPC configuration and that the fleet security group does not expose unnecessary ports.

