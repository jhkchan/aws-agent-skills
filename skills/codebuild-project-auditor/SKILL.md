---
name: codebuild-project-auditor
description: >-
  Audits AWS CodeBuild projects for privileged mode (Docker-in-Docker host
  kernel access), plaintext secrets in environment variables, unencrypted S3
  logs and build artifacts, over-permissive service-role blast radius
  (PassRole, admin wildcard), VPC/network exposure, and public build-status
  badge leakage. Emits a deterministic verdict (PRIVILEGED | SECRET_LEAK |
  NO_ENCRYPTION | OVERPERMISSIVE_ROLE | CONFIG_GAP | OK) per project with
  enumerated findings and specific remediation. Use when reviewing CodeBuild
  projects, checking for privileged build containers, validating secret
  injection posture, auditing build-role IAM scope, hardening build-network
  isolation, or verifying encryption of logs and artifacts before production
  deployment.
version: 0.1.0
author: Jacky Chan — AWS Community Builder
license: Apache-2.0
compatibility: >-
  Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex,
  Gemini). No AWS CLI required for offline project-config classification.
  Live-account audits use aws codebuild batch-get-projects, aws iam
  list-attached-role-policies, aws iam list-role-policies, and aws iam
  get-role-policy (AWS CLI v2, SSO or key-based credentials).
keywords:
  - CodeBuild
  - build project
  - privileged mode
  - Docker-in-Docker
  - DinD
  - secret leak
  - environment variables
  - Secrets Manager
  - SSM Parameter Store
  - S3 logs encryption
  - SSE-KMS
  - build artifacts
  - service role
  - IAM blast radius
  - PassRole
  - admin wildcard
  - VPC config
  - build badge
  - badge enabled
  - public leak
  - build hardening
  - container security
tags: [codebuild, devtools, security, build-pipeline, privileged-mode, secrets, iam, encryption, vpc, audit]
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: true
  phase: 2
  supports_pipeline: true
  entry_point: false
  family: Developer Tools
  verdict_shape: "PRIVILEGED | SECRET_LEAK | NO_ENCRYPTION | OVERPERMISSIVE_ROLE | CONFIG_GAP | OK"
  when_to_use: >-
    Reviewing a CodeBuild project before production deployment, checking for
    privileged build containers, auditing secret-handling posture, validating
    that S3 logs and build artifacts are SSE-KMS encrypted, scoping down the
    CodeBuild service role, hardening VPC isolation for build network
    egress, or auditing the public build-status badge exposure across an
    account.
  activation_triggers:
    - "audit this CodeBuild project"
    - "is my CodeBuild container privileged"
    - "check CodeBuild for secrets in env vars"
    - "CodeBuild S3 logs unencrypted"
    - "CodeBuild service role too permissive"
    - "CodeBuild build badge public"
    - "harden my CodeBuild project"
    - "CodeBuild VPC config missing"
    - "CodeBuild IAM blast radius"
  invocation_schema: >-
    Input: either (a) a CodeBuild project configuration JSON document
    (describe-project output) optionally paired with the service-role
    identity-based policy, OR (b) a project name/ARN for live-account audit.
    Output: deterministic PROJECT/VERDICT/REASON/FINDINGS/REMEDIATION block
    per project, where VERDICT is in {PRIVILEGED, SECRET_LEAK, NO_ENCRYPTION,
    OVERPERMISSIVE_ROLE, CONFIG_GAP, OK, ERROR}.
---

# CodeBuild Project Auditor

## Mindset

**One-line takeaway:** the verdict is always the **worst** finding across
six ordered dimensions, and the priority is strict —
`PRIVILEGED > SECRET_LEAK > NO_ENCRYPTION > OVERPERMISSIVE_ROLE > CONFIG_GAP > OK`.

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

## Quick reference — verdict thresholds

| Condition | Verdict | Step |
|---|---|---|
| `environment.privilegedMode: true` on a non-Docker build | **PRIVILEGED** | Step 1 |
| `environment.privilegedMode: true` on a Docker build with no fileSystemLocations and noSYS_ADMIN cap | **PRIVILEGED** | Step 1 |
| Plaintext secret-pattern value in `environment.environmentVariables` (type PLAINTEXT/omitted) | **SECRET_LEAK** | Step 2 |
| `s3LogsConfig.encryptionDisabled: true` | **NO_ENCRYPTION** | Step 3a |
| `artifacts.encryptionDisabled: true` | **NO_ENCRYPTION** | Step 3b |
| `s3LogsConfig.status: ENABLED` and no `kmsKeyArn` and no SSE-S3-only justification | **NO_ENCRYPTION** | Step 3c |
| Service-role statement with `Action: "*"` on `Resource: "*"` | **OVERPERMISSIVE_ROLE** | Step 4a |
| Service-role grants `iam:PassRole` / `sts:AssumeRole` on `"*"` | **OVERPERMISSIVE_ROLE** | Step 4b |
| Service-role trust policy not scoped to project ARN via `aws:SourceArn`/`sts:ExternalId` | **OVERPERMISSIVE_ROLE** (sub-finding) | Step 4c |
| No `vpcConfig` and the project fetches secrets/artifacts cross-VPC | **CONFIG_GAP** | Step 5a |
| `badgeEnabled: true` | **CONFIG_GAP** | Step 6 |
| `logsConfig.cloudWatchLogs.status: DISABLED` and `s3LogsConfig.status: DISABLED` | **CONFIG_GAP** (forensics gap) | Step 7a |
| All dimensions pass | **OK** | Step 8 |

See the ordered steps below for edge cases. Deep CodeBuild internals
(build-host isolation, secrets-resolution pipeline, fleet multi-tenancy)
are in the [Deep reference](#deep-reference-codebuild-internals) section
at the end.

## Pre-flight: project metadata gate (run before classification)

Before classifying, sanity-check the project. Several attributes
**short-circuit** the audit — misclassifying them produces false positives
that erode trust.

**Multi-project / account-wide sweep note (pagination):** when auditing
every project in an account, `aws codebuild list-projects` returns at most
100 per page. Use `--next-token` from the prior `nextToken` to page
through. For each project name, also page the service-role policy
enumeration: `aws iam list-role-policies`, `aws iam list-attached-role-policies`,
and `aws iam get-policy-version` for each attached managed policy. Always
drain `nextToken` to completion — the long tail is where stale, exposed, or
forgotten projects live.

**Live-account pre-flight checks (skip if doing offline project-config
audit):**
1. Verify the caller's identity can run `codebuild:DeleteProject` /
   `UpdateProject` if remediation is intended — most read-only auditor
   roles CANNOT. Surface this BEFORE the operator approves the change.
2. Verify CloudTrail is logging CodeBuild **data events** for
   `StartBuild` / `StopBuild` / `BatchGetBuilds`. Management events are on
   by default, but build-batch and report data events must be explicitly
   enabled. Without them, build-source forensics have no signal.
3. Snapshot the current buildspec and project config BEFORE any edit —
   `batch-get-projects` is not versioned. There is no undo without a
   backup file.

| Attribute | Value | Effect on audit |
|---|---|---|
| `projectVisibility` | `PUBLIC_READ` | **Public project** — any AWS account can start builds. Treat as CRITICAL-level misconfiguration regardless of other dimensions. Output a separate `VISIBILITY_PUBLIC` finding and refuse to remediate inline; quarantine the project. |
| `environment.type` | `LINUX_CONTAINER` / `WINDOWS_SERVER_2019_CONTAINER` / `ARM_CONTAINER` | Standard container fleet. Proceed with audit. |
| `environment.image` | `aws/codebuild/standard:*` | **AWS-managed image.** Runs as non-root `codebuild-user` by default. Still audit privilegedMode and env vars. |
| `environment.image` | Custom (e.g. ECR ARN) | **Custom image.** Verify the image runs as non-root; if the Dockerfile ends with `USER root` or omits USER, the build runs as root inside the container (separate from privilegedMode). Note as INSECURE sub-finding. |
| `environment.computeType` | `BUILD_GENERAL1_LARGE` / `BUILD_GENERAL1_XLARGE` | Compute tier — operational, not security. |
| `source.type` | `GITHUB` / `BITBUCKET` / `CODECOMMIT` etc. | Source provider. If `GITHUB` with `webhook: true`, any push to the configured repo triggers a build — review whether PR builds run with the same elevated role. |
| `cache.type` | `S3` | S3 cache. Verify the cache bucket is in the same account and has BLOCK_PUBLIC_ACCESS on. |
| `cache.type` | `LOCAL` | Local cache (instance-only). No S3 exposure. |
| `encryptionKey` (top-level) | omitted | **AWS-managed SSE-KMS key** for CodeBuild artifacts. Acceptable defense-in-depth baseline. |
| `encryptionKey` (top-level) | Customer key ARN | Customer-managed SSE-KMS key. OK. |

**If the project config JSON is malformed** (invalid JSON, missing `source`
or `environment`), output:

```text
PROJECT: <name>
VERDICT: ERROR
REASON: Project config is not valid JSON or is missing required fields — cannot classify.
REMEDIATION: Retrieve the canonical config with `aws codebuild batch-get-projects --names <name> --output json` and re-audit.
```

## Process — Classification logic (apply in order, aggregate worst)

### Step 0: Expert knowledge — non-obvious CodeBuild behaviors that change classification

These behaviors are easy to misjudge without operational CodeBuild
experience. Each changes a verdict if ignored:

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

### Step 1: Privileged mode — Docker-in-Docker classification

If `environment.privilegedMode` is `true`:

- If `source.buildspec` (inline) contains no `docker build`, `docker
  push`, `docker run`, `docker-compose`, or `buildctl` usage → **PRIVILEGED**.
  The build has host-equivalent container privileges for no Docker reason.
- If `source.buildspec` is NOT set (buildspec comes from source repo)
  → **PRIVILEGED** with a NOTE: "Buildspec from source — fetch the
  branch's `buildspec.yml` to confirm Docker requirement:
  `aws codecommit get-file --repository-name <r> --commit-specifier <branch> --file-path buildspec.yml`
  (CodeCommit) or `gh api repos/<owner>/<repo>/contents/buildspec.yml?ref=<branch>`
  (GitHub). Treat privilegedMode as active host access until verified."
- If the inline buildspec explicitly runs Docker commands → NOT a
  PRIVILEGED finding. Privileged mode is the documented mechanism for
  DinD. Note in FINDINGS: "[OK] privilegedMode enabled for Docker-in-Docker
  build — expected." Also emit a Step 7e NOTE about ECR scan-on-push.
- If `environment.privilegedMode: true` AND `environment.image` is a
  Docker-in-Docker image (`docker:dind`, `jpetazzo/dind`) → NOT a
  PRIVILEGED finding. The image is purpose-built.

If `privilegedMode` is `false` or omitted → no PRIVILEGED dimension.

### Step 2: Plaintext secret leak classification

For each entry in `environment.environmentVariables`:

- If `type` is omitted or `PLAINTEXT`: the value is committed plaintext.
  Apply the **secret-pattern heuristics** to the value:
  - Key name matches: `(?i).*(password|passwd|pwd|secret|api[_-]?key|access[_-]?key|secret[_-]?key|private[_-]?key|token|client[_-]?secret|db[_-]?pass|creds?|auth).*$`
  - Value matches AWS key patterns: `AKIA[0-9A-Z]{16}` (access-key-id),
    `aws4_request` signature fragments, `-----BEGIN .* PRIVATE KEY-----`
  - Value matches high-entropy strings (>=32 chars, mixed case+digits) when
    the key name is secret-shaped
- If a plaintext entry matches any pattern → **SECRET_LEAK**.
- If `type: PARAMETER_STORE` or `SECRETS_MANAGER` → NOT plaintext. The
  entry stores a parameter/secret ARN reference; the value is fetched at
  build time. Do NOT flag.
- `environment.secretsManager[]` entries are ALWAYS reference-based. Do
  NOT flag.

**Subtle distinction:** a variable named `DATABASE_URL` with value
`postgres://user:pass@host:5432/db` is a SECRET_LEAK — the password is
embedded in the URL. Apply URL-pattern detection: `^[a-z]+://[^:]+:[^@]+@`.

### Step 3: Encryption posture — S3 logs and build artifacts

Apply in order; first hit wins for the dimension:

- **3a.** If `s3LogsConfig.status: ENABLED` and
  `s3LogsConfig.encryptionDisabled: true` → **NO_ENCRYPTION**. The logs
  bucket receives build logs without customer-managed SSE-KMS.
- **3b.** If `artifacts.encryptionDisabled: true` → **NO_ENCRYPTION**.
  Build output artifacts are written without SSE-KMS.
- **3c.** If `s3LogsConfig.status: ENABLED` and `s3LogsConfig.kmsKeyArn`
  is omitted/empty → **NO_ENCRYPTION**. The logs use SSE-S3 only (no
  customer-managed key). The field is the only way to opt into SSE-KMS;
  omitting it means default-only encryption.
- **3d.** If `s3LogsConfig.status: DISABLED` and
  `cloudWatchLogs.status: ENABLED` → no NO_ENCRYPTION dimension (CloudWatch
  logs are encrypted by default, server-side). Note: log-group KMS
  encryption is a separate dimension (Step 7b).
- If `s3LogsConfig.encryptionDisabled: false` AND `kmsKeyArn` set → OK
  for this dimension.

### Step 4: Service-role blast radius

Examine the service role's identity-based policy (inline + attached). If
no policy document is provided in input, output a NOTE: "service-role
policy not supplied — IAM dimension cannot be evaluated statically. Run
`aws iam list-role-policies --role-name <role>` and re-audit." Do NOT
guess a verdict for the missing dimension.

For each `Effect: Allow` statement in the role's identity-based policy:

- **4a.** `Action: "*"` AND `Resource: "*"` → **OVERPERMISSIVE_ROLE**
  (admin wildcard). Highest-severity role finding.
- **4b.** Any of `iam:PassRole`, `sts:AssumeRole`,
  `iam:CreatePolicy`, `iam:AttachRolePolicy`, `iam:PutRolePolicy`,
  `iam:UpdateAssumeRolePolicy` on `Resource: "*"` →
  **OVERPERMISSIVE_ROLE** (privilege-escalation vector).
- **4c.** Service-wildcard action (`s3:*`, `ec2:*`, `secretsmanager:*`,
  `kms:*`, `ssm:*`, `lambda:*`, `cloudformation:*`) on `Resource: "*"` →
  **OVERPERMISSIVE_ROLE** (service-level wildcard on all resources).
- **4d.** Trust policy (`assumeRolePolicyDocument`) Principal is
  `{"Service": "codebuild.amazonaws.com"}` with NO `Condition` block
  scoping `aws:SourceArn` or `aws:SourceAccount` to this project →
  **OVERPERMISSIVE_ROLE** sub-finding (confused-deputy vector). Any
  CodeBuild project in the account can assume this role. The remediation
  is adding `Condition: {StringEquals: {"aws:SourceArn": "<project-arn>"}}`.

If all role statements have named actions on specific ARNs AND the trust
policy is scoped → OK for this dimension.

### Step 5: VPC configuration — network exposure

- **5a.** No `vpcConfig` block AND the project fetches secrets / writes
  artifacts to cross-VPC resources → **CONFIG_GAP**. The build has direct
  internet egress (default network), which is an exfiltration path for
  any secret the build can read. If all source/artifact/secret resources
  are public-internet-hosted (e.g., public GitHub, public PyPI), no
  CONFIG_GAP — the build has nothing to exfiltrate to a private endpoint.
- **5b.** `vpcConfig` present AND `subnets` are all public subnets
  (route table includes `0.0.0.0/0` via IGW) → **CONFIG_GAP**. The build
  is "in a VPC" but still has direct internet egress — the VPC adds no
  isolation. Use private subnets + NAT gateway for true egress control.
- **5c.** `vpcConfig` present with private subnets and security groups
  that allow `0.0.0.0/0` egress → **CONFIG_GAP** (overly broad SG).
- **5d.** `vpcConfig` present with private subnets, restrictive SG, and
  no NAT (air-gapped) → OK.

If you cannot determine subnet type (offline audit with only project
config) AND `vpcConfig` is present, treat as OK for this dimension with a
NOTE: "subnet classification requires DescribeRouteTables; treat as
verified post-check."

### Step 6: Build badge — public status leakage

If `badgeEnabled: true`:

- The badge URL is `https://codebuild.<region>.amazonaws.com/badges/api/v1/project/<hash>/branch/<branch>/status.svg`
- This URL is **publicly accessible without authentication**. Anyone with
  the URL (or who guesses/enumerates it) can see the latest build status
  for the branch. The URL does NOT reveal the project name directly, but
  it confirms the project exists and leaks branch build state.
- **CONFIG_GAP** finding. The risk is information disclosure: a competitor
  or attacker can see whether your builds are passing, infer release
  cadence, and time attacks around known broken-build windows.
- If the badge is intentionally used for a public OSS project README →
  note as expected, but still emit the finding (the leak is real even if
  intentional).

### Step 7: Other configuration gaps

- **7a. Forensics gap.** If `logsConfig.cloudWatchLogs.status: DISABLED`
  AND `s3LogsConfig.status: DISABLED` → **CONFIG_GAP**. No build logs are
  captured. Incident response has no signal — a compromised build leaves
  no trace. At least one logs destination must be enabled.
- **7b. CloudWatch log group KMS.** If `cloudWatchLogs.status: ENABLED`
  and the log group has no KMS key associated (CloudWatch Logs
  server-side encryption is default but not customer-managed) →
  **CONFIG_GAP** sub-finding. Use `aws logs associate-kms-key` on the
  build log group.
- **7c. FileSystem locations.** If `fileSystemLocations` is non-empty and
  any entry's `identifier` references an EFS without an account-scoped
  filesystem policy → **CONFIG_GAP** sub-finding.
- **7d. Cache bucket exposure.** If `cache.type: S3` and the cache bucket
  has BLOCK_PUBLIC_ACCESS off → **CONFIG_GAP**. Cache poisoning is a
  supply-chain vector.
- **7e. ECR scan-on-push for built images.** If the inline buildspec runs
  `docker push` to an ECR repository and the ECR repo has
  `scanOnPush: false` → **CONFIG_GAP** sub-finding. The build produces
  unscanned images that downstream services deploy blindly. The fix is on
  the ECR repo, not the CodeBuild project:
  `aws ecr put-image-scanning-configuration --repository-name <r> --image-scanning-configuration scanOnPush=true`.

### Step 8: Aggregation — worst finding wins

The final verdict is the **maximum severity** across all dimensions, where
PRIVILEGED > SECRET_LEAK > NO_ENCRYPTION > OVERPERMISSIVE_ROLE >
CONFIG_GAP > OK:

```text
verdict = max(step1, step2, step3, step4, step5, step6, step7)
```

If no findings, verdict is **OK**.

## Output format (per project)

```text
PROJECT: <name>
VERDICT: PRIVILEGED | SECRET_LEAK | NO_ENCRYPTION | OVERPERMISSIVE_ROLE | CONFIG_GAP | OK
REASON: <1-2 sentences citing the worst finding and its step>
FINDINGS:
  - [PRIVILEGED] <finding description (Step Na)>
  - [CONFIG_GAP] <finding description (Step Nb)>
REMEDIATION: <specific action per finding, or "None required" if OK>
```

### Worked example — privileged build with plaintext secret

```text
PROJECT: payments-ci
VERDICT: PRIVILEGED
REASON: environment.privilegedMode is true and the inline buildspec contains
no Docker commands (Step 1) — host-equivalent container privilege with no
Docker justification. Also leaks DB_PASSWORD in plaintext env vars.
FINDINGS:
  - [PRIVILEGED] privilegedMode true with non-Docker buildspec (Step 1)
  - [SECRET_LEAK] environmentVariables[DB_PASSWORD] type=PLAINTEXT (Step 2)
  - [OVERPERMISSIVE_ROLE] service role grants s3:* on "*" (Step 4c)
REMEDIATION:
  1. Disable privilegedMode (full-environment JSON replace):
     aws codebuild batch-get-projects --names payments-ci --query 'projects[0].environment' --output json > /tmp/env.json
     edit /tmp/env.json to set "privilegedMode": false
     aws codebuild update-project --name payments-ci --environment file:///tmp/env.json
  2. Move DB_PASSWORD to Secrets Manager: create the secret, then edit
     the same /tmp/env.json to drop the plaintext entry and add it to
     the secretsManager array, then re-apply update-project.
  3. Scope the service role's s3 actions to the specific bucket ARN.
```

## Edge-case handling

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

## Anti-Patterns — NEVER

- NEVER classify `privilegedMode: true` on a Docker-build project as
  PRIVILEGED. DinD requires privileged mode; the flag is the documented
  mechanism. Verify the buildspec before flagging.

- NEVER classify `type: PARAMETER_STORE` or `type: SECRETS_MANAGER`
  environment variables as SECRET_LEAK. These store only ARN references;
  the value is fetched at build time and never appears in the project
  config. The leak channel is closed by design.

- NEVER flag the absence of `kmsKeyArn` on `s3LogsConfig` as NO_ENCRYPTION
  when `encryptionDisabled` is also false and SSE-S3 default encryption
  is the documented organizational baseline. Re-read the org policy
  before flagging — some orgs explicitly accept SSE-S3 for build logs.

- NEVER treat a CodeBuild service role's `codebuild:*` on the project
  ARN as over-permissive. CodeBuild projects REQUIRE `codebuild:CreateReport`,
  `codebuild:UpdateReport`, `codebuild:BatchPut*` to function. These are
  baseline permissions, not wildcards.

- NEVER recommend deleting a project as remediation without snapshotting
  the config first. `delete-project` is irreversible; project configs are
  not versioned. Run `aws codebuild batch-get-projects --names <n> --output json`
  to a backup file first.

- NEVER assume the inline buildspec matches the source-repo buildspec.
  If `source.buildspec` is set, the inline YAML wins — the repo's
  `buildspec.yml` is IGNORED. A PR that modifies the repo buildspec has
  no effect when the inline override is in place. This is a SECURITY
  BENEFIT (deterministic buildspec), not a config gap.

- NEVER flag `concurrentBuildLimit` or `queuedRetry` as findings. These
  are operational knobs, not security posture.

- NEVER assume `vpcConfig` presence equals isolation. A VPC with public
  subnets provides zero isolation over the default network. The
  subnet-route-table check (Step 5b) is what determines real isolation.

- NEVER recommend flipping `encryptionDisabled: true` to false on a
  legacy cross-account artifacts setup without explaining the migration
  path. The setting exists because cross-account SSE-KMS used to require
  it. The fix is a customer-managed KMS key with a key policy granting
  the cross-account principal `kms:Decrypt`.

- NEVER classify `badgeEnabled: true` as anything other than CONFIG_GAP.
  It is information disclosure, not a privilege escalation. Downgrading
  the verdict because the project is "internal" misses the point — the
  badge URL is publicly reachable without auth.

- NEVER skip the service-role trust policy check. The trust policy
  determines WHO can assume the role; an unscoped trust policy is the
  confused-deputy vector that lets any CodeBuild project in the account
  use this role.

- NEVER assume the AWS-managed CodeBuild image runs as root. The default
  `aws/codebuild/standard:*` images run as the non-root `codebuild-user`.
  A `user: root` finding requires either a custom image with `USER root`
  or an explicit `user` override in the project config (which CodeBuild
  does not expose — it is image-driven).

- NEVER treat a missing service-role policy document as an
  OVERPERMISSIVE_ROLE finding. You cannot statically classify what you
  cannot see. Output a NOTE and require the operator to provide the
  policy. Guessing produces false positives.

- NEVER recommend `projectVisibility: PUBLIC_READ` as a way to "share a
  build with a partner account." Use a cross-account IAM role assumption
  instead. PUBLIC_READ makes the project startable by EVERY AWS account,
  not just the partner.

- NEVER overlook the cache bucket. `cache.type: S3` creates an S3 bucket
  that the build reads and writes on every run. If that bucket has public
  access or is in a different account, the cache is a supply-chain
  poisoning vector. Always verify S3 Block Public Access is ON for the
  cache bucket: `aws s3api get-public-access-block --bucket <b>`. A
  poisoned cache (a tampered `.tar` archive) executes arbitrary code in
  every subsequent build that unpacks it — a SolarWinds-style upstream
  vector.

- NEVER conflate `environment.image` (the build container image) with
  `source` (the Git repo). The image determines what runs; the source
  determines what gets built. A clean image + malicious source is a
  compromised build; a malicious image + clean source is a compromised
  build environment.

- NEVER allow wildcard actions in the service-role TRUST policy
  (`assumeRolePolicyDocument`). The Principal must be
  `{"Service": "codebuild.amazonaws.com"}` (singular, service-scoped) —
  never `{"AWS": "*"}` or `{"AWS": "arn:aws:iam::cloudroot"}`. The
  Condition must include `aws:SourceArn` or `aws:SourceAccount` scoped to
  the project — without it, ANY CodeBuild project in the account (or any
  principal if `{"AWS": "*"}`) can assume the role. This is the confused-
  deputy vector that the console-generated trust policy omits by default.

- NEVER treat `source.auth.resource` as the credential itself. It is a
  CodeBuild-generated ARN referencing a server-side stored token. The
  token is not in the project config; you cannot rotate it from
  `update-project`. Rotate via `aws codebuild import-source-credentials`
  with a fresh token, or sever the connection and re-import.

## Pre-flight safety checks (run before any remediation CLI)

- **MANDATORY CONFIRMATION GATE.** Before any state-changing operation
  (`update-project`, `delete-project`, `put-role-policy`,
  `create-project`), the auditor MUST emit:
  `CONFIRM: About to <action> on project <name> in account <account>.
  This affects <consequence>. Proceed? (yes/no)`
  Do NOT execute the CLI command until the operator confirms. This gate
  prevents automated pipelines from silently modifying build projects.
- **Snapshot the current project config for rollback:**
  `aws codebuild batch-get-projects --names <name> --output json > /tmp/<name>-backup-$(date +%s).json`
  BEFORE any modification. CodeBuild project configs are NOT versioned —
  there is no undo without a backup.
- **Snapshot the service-role policy for rollback:**
  `aws iam list-role-policies --role-name <role> --output json > /tmp/<role>-inline-$(date +%s).json`
  and
  `aws iam list-attached-role-policies --role-name <role> --output json > /tmp/<role>-attached-$(date +%s).json`.
  Inline and attached IAM policies are not versioned by default — a
  `put-role-policy` replaces inline content atomically with no rollback.
- **Verify the build is not currently running** before disabling
  `privilegedMode` on a Docker-build project. An in-flight Docker build
  will fail mid-flight when privilegedMode flips. Use
  `aws codebuild batch-get-builds --ids <build-id>` to check status.
- **Confirm the Secrets Manager secret exists and is resolvable** before
  moving a plaintext env var to `secretsManager`. A broken secret
  reference breaks the build. Use
  `aws secretsmanager describe-secret --secret-id <id>` first.
- **Prefer additive changes** (add a condition, scope a resource) over
  destructive changes (remove a statement, delete a variable) — additive
  changes are reversible and do not risk breaking existing builds.

## Remediation guidance

**Ordering principle:** additive before destructive. Add a scoped
statement BEFORE removing a wildcard one. Add a condition BEFORE removing
an unconditional principal.

### For PRIVILEGED — privilegedMode enabled on non-Docker build

1. Verify the buildspec does not run Docker: check `source.buildspec`
   for `docker`, `buildctl`, `docker-compose`.
2. Re-fetch the full current environment block (the update is a
   full-replace, not a patch):
   `aws codebuild batch-get-projects --names <n> --query 'projects[0].environment' --output json > /tmp/<n>-env.json`.
3. Edit `/tmp/<n>-env.json` to set `"privilegedMode": false`.
4. Apply the full environment JSON:
   `aws codebuild update-project --name <n> --environment file:///tmp/<n>-env.json`.
5. Confirm by re-fetching:
   `aws codebuild batch-get-projects --names <n> --query 'projects[0].environment.privilegedMode'`.
6. If the build actually needs Docker, leave privilegedMode on and add
   a NOTE: "privilegedMode required for Docker-in-Docker build — no
   remediation."

### For SECRET_LEAK — plaintext secret in environment variables

1. Identify the leaked variable(s). Each must move to a secure channel.
2. Create a Secrets Manager secret (if not already):
   `aws secretsmanager create-secret --name <project>/<var> --secret-string <value>`.
3. Re-fetch the full environment block (full-replace update):
   `aws codebuild batch-get-projects --names <n> --query 'projects[0].environment' --output json > /tmp/<n>-env.json`.
4. In `/tmp/<n>-env.json`: (a) remove the leaked entry from
   `environmentVariables`, (b) add a `secretsManager` array entry
   `{"secretsManagerArn":"arn:aws:secretsmanager:...","name":"<var>","type":"SECRETS_MANAGER"}`
   if not already present.
5. Apply: `aws codebuild update-project --name <n> --environment file:///tmp/<n>-env.json`.
6. **Rotate the leaked credential.** The plaintext value was visible in
   CloudTrail, the API, and the console for the lifetime of the
   project config. Treat it as compromised.
7. Audit CloudTrail for `BatchGetProjects` API calls during the exposure
   window — any principal with `codebuild:BatchGetProjects` read the
   plaintext secret.

### For NO_ENCRYPTION — S3 logs or artifacts without SSE-KMS

1. Create or identify a customer-managed KMS key:
   `aws kms create-key --description "CodeBuild <project> SSE-KMS key"`.
2. Update the key policy to grant the CodeBuild service role
   `kms:GenerateDataKey*` and `kms:Decrypt` on the key.
3. For S3 logs: re-fetch the full logs-config block:
   `aws codebuild batch-get-projects --names <n> --query 'projects[0].logsConfig' --output json > /tmp/<n>-logs.json`,
   then edit `s3Logs.encryptionDisabled` to `false` and set
   `s3Logs.kmsKeyArn` to the key ARN. Apply with
   `aws codebuild update-project --name <n> --logs-config file:///tmp/<n>-logs.json`.
4. For artifacts: re-fetch `projects[0].artifacts` to a file, edit
   `encryptionDisabled` to `false`, and apply with
   `aws codebuild update-project --name <n> --artifacts file:///tmp/<n>-artifacts.json`.
   The top-level artifact-encryption key is also settable via
   `--encryption-key <key-arn>`.
5. For legacy cross-account artifacts, migrate to a customer-managed KMS
   key with a key policy granting the cross-account principal
   `kms:Decrypt`. Do NOT flip `encryptionDisabled` to false without the
   key policy in place — the cross-account build will fail.

### For OVERPERMISSIVE_ROLE — service role blast radius

1. Snapshot the current role policy (see Pre-flight).
2. Replace wildcard actions with named actions derived from CloudTrail
   `AssumedRole` events for the role (90-day window minimum).
3. Replace `Resource: "*"` with the specific ARNs the build actually
   accesses (S3 buckets, ECR repos, KMS keys, Secrets Manager secrets).
4. For `iam:PassRole`: scope to the specific role ARN(s) the build
   passes, and add `iam:PassedToService` condition to constrain which
   service receives the role.
5. For the trust policy: add
   `Condition: {StringEquals: {"aws:SourceArn": "arn:aws:codebuild:<region>:<account>:project/<name>"}}`
   to scope assumption to this project only.
6. Validate with `aws iam simulate-principal-policy --policy-source-arn <role-arn> --action-names <list>`.

### For CONFIG_GAP — VPC / badge / forensics / cache

- **VPC missing (Step 5a):** create a VPC with private subnets, NAT
  gateway, and restrictive security groups. Re-fetch any existing
  vpcConfig block first, then apply the full JSON:
  `aws codebuild update-project --name <n> --vpc-config '{"vpcId":"vpc-aaa","subnets":["subnet-private-1"],"securityGroupIds":["sg-build-egress-only"]}'`.
- **Public subnets (Step 5b):** move the build to private subnets. Update
  route tables or change the subnet list (full-replace via `--vpc-config`).
- **Badge enabled (Step 6):** disable with the toggle flag:
  `aws codebuild update-project --name <n> --no-badge-enabled`.
- **No logs (Step 7a):** enable at least CloudWatch Logs by passing the
  full logs-config JSON:
  `aws codebuild update-project --name <n> --logs-config '{"cloudWatchLogs":{"status":"ENABLED"},"s3Logs":{"status":"DISABLED"}}'`.
- **CloudWatch no KMS (Step 7b):** associate a key:
  `aws logs associate-kms-key --log-group-name <group> --kms-key-id <key-id>`.
- **Cache bucket exposed (Step 7d):** enable S3 Block Public Access on
  the cache bucket:
  `aws s3api put-public-access-block --bucket <b> --public-access-block-configuration BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true`.

### For OK

1. No remediation required.
2. Recommend enabling CloudWatch Logs with SSE-KMS as defense-in-depth.
3. Recommend scoping the service-role trust policy to the project ARN if
   not already scoped.

## Deep reference: CodeBuild internals

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

## Domain

AWS CloudOps / Developer Tools (CodeBuild) Security & Compliance.
