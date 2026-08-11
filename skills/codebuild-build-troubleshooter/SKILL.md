---
name: codebuild-build-troubleshooter
description: >-
  Diagnoses AWS CodeBuild build failures through a stopped-phase-first
  diagnostic tree: BUILD_CONTAINER_UNABLE_TO_PULL_IMAGE (ECR auth, image
  size, Docker Hub rate limit), phase-level command failures (INSTALL,
  PRE_BUILD, BUILD, POST_BUILD), buildspec.yml syntax and version errors,
  environment variable resolution (Plaintext, SecretsManager,
  SSM Parameter Store), artifact upload failures (S3 permissions, KMS
  encryption, packaging), VPC config errors (subnet, SG, NAT Gateway),
  runtime version mismatch (unsupported runtimes, deprecated images),
  build timeout (queuing vs execution), source checkout failures
  (CodeCommit auth, GitHub token, secondary sources), caching issues
  (LOCAL_DOCKER_LAYER, LOCAL_SOURCE_CACHE, S3 cache bucket permissions),
  privileged-mode Docker builds, secret manager integration failures, and
  batch configuration errors. Walks phase status, logs, and project config
  to a verified root cause with evidence-backed probes. Emits
  ROOT_CAUSE_IDENTIFIED or INSUFFICIENT_DATA.
version: 0.1.0
author: Jacky Chan — AWS Community Builder
license: Apache-2.0
compatibility: >-
  Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex,
  Gemini). Offline diagnosis works on supplied batch-get-builds JSON, log
  excerpts, and buildspec.yml. Live-account diagnosis uses aws codebuild
  batch-get-builds, batch-get-projects, aws logs get-log-events /
  filter-log-events, aws iam simulate-principal-policy, aws ecr
  get-repository-policy / describe-images, aws s3api get-bucket-policy /
  get-bucket-location, aws secretsmanager describe-secret, aws ssm
  get-parameter, aws ec2 describe-subnets / describe-security-groups /
  describe-route-tables (AWS CLI v2, SSO or key-based credentials).
keywords:
  - CodeBuild
  - buildspec
  - BUILD_CONTAINER_UNABLE_TO_PULL_IMAGE
  - phase error
  - INSTALL phase
  - PRE_BUILD phase
  - BUILD phase
  - POST_BUILD phase
  - Docker build
  - privileged mode
  - ECR pull
  - artifact upload
  - S3 artifact
  - VPC config
  - runtime version
  - build timeout
  - source checkout
  - CodeCommit auth
  - GitHub source
  - local cache
  - S3 cache
  - Secrets Manager
  - build badge
  - queued build
  - batch build
tags:
  - codebuild
  - devtools
  - troubleshoot
  - build-failure
  - buildspec
  - ecr
  - docker
  - vpc
  - caching
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: true
  phase: 2
  supports_pipeline: true
  entry_point: false
  family: DevTools
  task_type: troubleshoot
  skill_class: capability
  lifecycle_status: active
  verdict_shape: "ROOT_CAUSE_IDENTIFIED | INSUFFICIENT_DATA"
  when_to_use: >-
    Diagnosing why a CodeBuild build fails or behaves unexpectedly — phase
    command failures (INSTALL/PRE_BUILD/BUILD/POST_BUILD), image pull errors
    (BUILD_CONTAINER_UNABLE_TO_PULL_IMAGE), buildspec syntax errors,
    environment variable resolution failures, artifact upload errors,
    VPC-related build failures (no NAT, SG blocking), runtime version
    mismatch, build timeout, source checkout failures (CodeCommit/GitHub),
    cache misses or misconfiguration, Docker-in-Docker build failures
    (privileged mode), Secrets Manager / SSM Parameter Store integration
    errors, build badge generation failures, queued build concurrency
    limits, or batch build configuration errors.
  when_not_to_use: >-
    Application code debugging inside a build (use the build logs and the
    application's own tests), CodePipeline orchestration debugging (use
    codepipeline-failure-troubleshooter), ECR repository policy audits
    (use ecr-repository-auditor), IAM least-privilege posture audits on
    the CodeBuild service role (use iam-least-privilege-advisor), or
    steady-state CodeBuild project configuration audits (use
    codebuild-project-auditor).
  activation_triggers:
    - "CodeBuild build failed"
    - "BUILD_CONTAINER_UNABLE_TO_PULL_IMAGE"
    - "CodeBuild phase error"
    - "CodeBuild INSTALL failed"
    - "CodeBuild PRE_BUILD failed"
    - "CodeBuild BUILD phase failed"
    - "CodeBuild buildspec error"
    - "CodeBuild Docker build failed"
    - "CodeBuild privileged mode"
    - "CodeBuild artifact upload failed"
    - "CodeBuild VPC build timeout"
    - "CodeBuild source checkout failed"
    - "CodeCommit clone failed"
    - "CodeBuild cache miss"
    - "CodeBuild S3 cache"
    - "CodeBuild Secrets Manager"
    - "CodeBuild runtime version"
    - "CodeBuild build timeout"
    - "CodeBuild queued build"
    - "CodeBuild batch build error"
  invocation_schema: >-
    Input: either (a) a symptom description (error message, failed phase
    name, observed build behaviour) optionally paired with the project
    name, build ID, and recent build logs, OR (b) a project name plus
    build context (region, source type, VPC config) for live-account
    diagnosis. Output: a deterministic TARGET/VERDICT/REASON/ROOT_CAUSE/
    EVIDENCE/REMEDIATION block where VERDICT is ROOT_CAUSE_IDENTIFIED or
    INSUFFICIENT_DATA, and ROOT_CAUSE is one of IMAGE_PULL_AUTH,
    IMAGE_PULL_SIZE, PHASE_COMMAND_FAIL, BUILDSPEC_SYNTAX,
    ENV_VAR_RESOLUTION, ARTIFACT_S3_PERMISSION, ARTIFACT_KMS,
    VPC_NO_EGRESS, VPC_SG_BLOCKING, RUNTIME_VERSION,
    BUILD_TIMEOUT_CONFIG, BUILD_TIMEOUT_DOWNSTREAM,
    SOURCE_CHECKOUT_AUTH, CACHE_S3_MISCONFIG, CACHE_LOCAL_MISCONFIG,
    DOCKER_PRIVILEGED_MODE, SECRET_ACCESS, BADGE_GENERATION,
    QUEUED_CONCURRENCY, BATCH_CONFIG, or UNKNOWN.
  invocation_example: >-
    # Minimal valid input (offline symptom classification):
    Symptom: "CodeBuild project cb-prod-api fails during the BUILD phase
    with 'Docker daemon not found' on every build."
    ProjectName: cb-prod-api
    BuildId: cb-prod-api:abc12345
    EnvironmentPrivilegedMode: false
    BuildspecPhase: BUILD
    LastPhaseStatus: FAILED
---

# CodeBuild Build Troubleshooter

## Quick start

- **Phase status drives the first probe.** `batch-get-builds` returns
  `phases[]` with `phaseType`, `phaseStatus`, `durationInSeconds`, and
  `contexts[].message`. The first `FAILED` phase is the entry point —
  not the overall build status. A build that fails in INSTALL has a
  completely different root cause from one that fails in BUILD or
  POST_BUILD.
- **BUILD_CONTAINER_UNABLE_TO_PULL_IMAGE is the highest-signal error
  string.** It points at ECR auth (service role missing ECR permissions),
  image size (exceeds the 15 GB uncompressed Docker storage cap), or
  Docker Hub rate limiting (no credential for `docker login`). Probe
  ECR repo policy, image size, and the service role's `ecr:*` permissions
  before anything else.
- **Docker-in-Docker builds require `privilegedMode: true`.** Without
  privileged mode, `docker build` inside the buildspec returns
  "Cannot connect to the Docker daemon" or "Docker daemon not found."
  This is the single most common CodeBuild Docker failure and is a
  project environment config issue, not a buildspec issue.
- **VPC-attached CodeBuild projects have the same egress rules as Lambda.**
  A build in a private subnet without a NAT Gateway cannot reach package
  registries (npm, PyPI, Maven), external Git repos, or Docker Hub.
  VPC-attached builds reach AWS services (S3, ECR, Secrets Manager) via
  VPC endpoints or NAT — never assume connectivity.
- **Cache mode matters.** `LOCAL_DOCKER_LAYER` caches Docker layers on
  the build host (requires privileged mode); `S3` cache stores compiled
  artifacts in an S3 bucket (requires `cache.bucket` + service role
  `s3:GetObject` / `s3:PutObject`). Mixing them up produces "cache miss"
  patterns that look like slow builds but are config errors.

## Quick reference — phase-to-cause navigation table

| Failed phase / error string | Most likely ROOT_CAUSE | First probe |
|---|---|---|
| `SUBMITTED` → `FAILED` before `QUEUED` | BATCH_CONFIG | `batch-get-projects` (batch config), buildspec `batch` block |
| `QUEUED` for long time, never `IN_PROGRESS` | QUEUED_CONCURRENCY | `batch-get-projects` (concurrent build limit), account Service Quotas |
| `PROVISIONING` → `FAILED` | VPC_NO_EGRESS / VPC_SG_BLOCKING | `batch-get-projects` (vpcConfig), `describe-subnets`, `describe-route-tables` |
| `DOWNLOAD_SOURCE` → `FAILED` | SOURCE_CHECKOUT_AUTH | `batch-get-builds` (sourceVersion, resolvedSourceVersion), CodeCommit/GitHub auth |
| `INSTALL` → `FAILED` | RUNTIME_VERSION / ENV_VAR_RESOLUTION | `batch-get-builds` (phases[].contexts), buildspec `phases.install` |
| `PRE_BUILD` → `FAILED` | PHASE_COMMAND_FAIL / DOCKER_PRIVILEGED_MODE | Build logs for the PRE_BUILD phase, `environment.privileged-mode` |
| `BUILD` → `FAILED` | PHASE_COMMAND_FAIL / DOCKER_PRIVILEGED_MODE / BUILD_TIMEOUT_DOWNSTREAM | Build logs for the BUILD phase |
| `POST_BUILD` → `FAILED` | PHASE_COMMAND_FAIL / ARTIFACT_S3_PERMISSION | Build logs, `batch-get-builds` (exportedEnvironmentVariables) |
| `UPLOAD_ARTIFACTS` → `FAILED` | ARTIFACT_S3_PERMISSION / ARTIFACT_KMS | Service role IAM, `artifacts.location`, `encryptionKey` |
| `BUILD_CONTAINER_UNABLE_TO_PULL_IMAGE` | IMAGE_PULL_AUTH / IMAGE_PULL_SIZE | ECR repo policy, image size, service role ECR permissions |
| `YAML_FILE_ERROR` / `Phase context status code` | BUILDSPEC_SYNTAX | `codebuild validate-buildspec`, buildspec YAML validation |
| Build badge 404 / not updating | BADGE_GENERATION | `batch-get-projects` (badgeEnabled), project visibility |
| Build exceeds timeout, phase `TIMED_OUT` | BUILD_TIMEOUT_CONFIG / BUILD_TIMEOUT_DOWNSTREAM | `batch-get-builds` (timeoutInMinutes), phase duration |
| Secrets Manager / SSM param unresolved | SECRET_ACCESS | Service role IAM for `secretsmanager:GetSecretValue` / `ssm:GetParameter` |

## STRICT output contract

Every diagnosis MUST emit exactly one block in this format:

```text
TARGET: <project-name / build-id>
VERDICT: ROOT_CAUSE_IDENTIFIED | INSUFFICIENT_DATA
REASON: <1-2 sentences naming the failed phase, the ROOT_CAUSE category,
  and the failing probe that confirms it>
ROOT_CAUSE: <IMAGE_PULL_AUTH | IMAGE_PULL_SIZE | PHASE_COMMAND_FAIL |
  BUILDSPEC_SYNTAX | ENV_VAR_RESOLUTION | ARTIFACT_S3_PERMISSION |
  ARTIFACT_KMS | VPC_NO_EGRESS | VPC_SG_BLOCKING | RUNTIME_VERSION |
  BUILD_TIMEOUT_CONFIG | BUILD_TIMEOUT_DOWNSTREAM |
  SOURCE_CHECKOUT_AUTH | CACHE_S3_MISCONFIG | CACHE_LOCAL_MISCONFIG |
  DOCKER_PRIVILEGED_MODE | SECRET_ACCESS | BADGE_GENERATION |
  QUEUED_CONCURRENCY | BATCH_CONFIG | UNKNOWN>
EVIDENCE:
  - Symptom: <observed error string or phase behaviour>
  - Failing probe: <command and output that confirms the cause>
  - Passing probes: <categories ruled out>
REMEDIATION:
  1. <specific action with CLI command>
  2. <verification command after the fix>
CONFIRM: Before executing any state-changing CLI, emit and await operator
  approval: "CONFIRM: About to <action> on <project> in <region>. Proceed?
  (yes/no)"
```

## NEVER

- **NEVER** declare `ROOT_CAUSE_IDENTIFIED` without a failing probe that
  matches the symptom. The phase status (`FAILED`) is a symptom, not a
  root cause; read the phase `contexts[].message` and the build logs
  before naming the category.

- **NEVER** confuse the service role with the source credential. The
  **service role** is assumed by CodeBuild at build time (permissions for
  the build to call AWS APIs — S3, ECR, Secrets Manager, SSM). The
  **source credential** is the OAuth token / SSH key used to clone the
  source repo (CodeCommit uses IAM; GitHub uses a stored personal access
  token or connection ARN). A `DOWNLOAD_SOURCE` failure is the source
  credential; a `CannotPullContainerError` from ECR is the service role.
  Swapping the two is the single most common CodeBuild misdiagnosis.

- **NEVER** recommend adding a NAT Gateway to fix a VPC-attached CodeBuild
  build without first checking for VPC endpoints. ECR interface endpoints
  (`com.amazonaws.<region>.ecr.api`, `com.amazonaws.<region>.ecr.dkr`)
  and the S3 gateway endpoint are cheaper and more secure. The NAT is
  required for external package registries (npm, PyPI, Maven), not for
  AWS services.

- **NEVER** assume `privilegedMode: false` is the default for all build
  environments. It is the default for new projects, but some existing
  projects may have it set to `true`. Docker-in-Docker builds (running
  `docker build` / `docker push` inside buildspec commands) REQUIRE
  `privilegedMode: true`. Without it, the Docker daemon is unavailable
  and every `docker` command fails.

- **NEVER** conflate `LOCAL_DOCKER_LAYER` cache with `S3` cache.
  `LOCAL_DOCKER_LAYER` caches Docker layers on the build host instance
  (ephemeral — only helps if the same host is reused; requires privileged
  mode). `S3` cache stores compiled artifacts / dependency caches in an
  S3 bucket (persistent across builds; requires bucket + IAM). Using the
  wrong mode produces "cache not helping" patterns.

- **NEVER** change the runtime version in a buildspec without checking
  the CodeBuild managed image support matrix. Runtime versions are
  removed when the underlying OS or language is deprecated (e.g.,
  `nodejs: 12`, `python: 3.7`). A removed runtime version produces
  `Phase context status code: YAML_FILE_ERROR` — which looks like a
  syntax error but is actually a runtime availability issue.

- **NEVER** conclude "build timed out" without distinguishing
  `TIMED_OUT` phase status (CodeBuild killed the build at
  `timeoutInMinutes`) from a downstream hang (a command in the buildspec
  hung on a network call). The former is a config issue (raise the
  timeout); the latter is a downstream dependency issue.

## Expert heuristic

> **Buildspec phase ordering is strictly sequential:** `INSTALL` →
> `PRE_BUILD` → `BUILD` → `POST_BUILD` → `UPLOAD_ARTIFACTS`. A failure
> in an earlier phase prevents later phases from running. Always read
> the first `FAILED` phase — it is the root cause, not a downstream
> symptom.
>
> **Docker builds inside CodeBuild require `environment.privileged-mode:
> true` on the project.** This is a project-level config, NOT a buildspec
> field. Without it, the Docker daemon is not started and every `docker`
> command in any phase returns "Cannot connect to the Docker daemon."
> The error surfaces in whichever phase first calls `docker build`.
>
> **Cache mode determines the storage backend and permissions:**
> - `LOCAL_DOCKER_LAYER` — on-host Docker layer cache; requires
>   `privilegedMode: true`; helps only if the same build host is reused.
> - `LOCAL_SOURCE_CACHE` — on-host Git source cache.
> - `LOCAL_CUSTOM_CACHE` — on-host custom paths defined in buildspec
>   `cache.paths`.
> - `S3` — persistent cache in `cache.bucket`; service role needs
>   `s3:GetObject` / `s3:PutObject` on `cache.bucket/*`.
>
> **VPC-attached CodeBuild builds in private subnets need a NAT Gateway
> for external egress.** Unlike Lambda (which can use the managed
> network without a VPC), a VPC-attached CodeBuild project is fully
> inside the VPC and follows standard VPC routing. The S3 + DynamoDB
> gateway endpoints are free; everything else needs an interface
> endpoint or NAT.

## Configuration dependency graph

```
                      CodeBuild project
                            │
         ┌─────────────────┼──────────────────────┐
         ▼                 ▼                      ▼
    environment       source               service role
    (image,           (type:               (assumed by CodeBuild;
     privileged-      CodeCommit /          permissions for S3,
     mode, runtime,   GitHub /              ECR, Secrets Manager,
     computeType,     S3 / Bitbucket)       SSM, CloudWatch Logs,
     environmentVariables,                    KMS)
     vpcConfig)              │
         │                   │                     │
         ▼                   ▼                     ▼
    buildspec.yml      source credential    IAM policy
    (phases:           (CodeCommit = IAM;   (ecr:*, s3:*,
     INSTALL,           GitHub = OAuth       secretsmanager:*,
     PRE_BUILD,         token stored as     ssm:GetParameter,
     BUILD,             a CodeBuild          logs:*,
     POST_BUILD,        source              kms:Decrypt)
     artifacts,         credential)
     cache)                                │
         │                                    │
         ▼                                    ▼
    cache config                           S3 bucket
    (type: LOCAL_* or S3;                 (artifacts +
     if S3: bucket + path)                cache bucket;
                                             encryptionKey)
         │
         ▼
    vpcConfig
    (subnets, securityGroups,
     if private subnet:
     need NAT for external
     egress or VPC endpoints
     for AWS services)
```

## Mindset

A failing CodeBuild build is usually a configuration or environment
issue, not a code bug. The buildspec commands are almost always correct;
the broken thing is the project environment (privileged mode, runtime,
VPC), the service role permissions (ECR, S3, Secrets Manager), the
source credential (CodeCommit IAM, GitHub token), or the cache config
(wrong mode, missing bucket permissions). Treat the buildspec commands
as innocent until the project config, service role, and environment
are proven correct.

Senior DevOps engineers do not start by reading the buildspec commands.
They start with `batch-get-builds`, read the first `FAILED` phase's
`contexts[].message`, and only open the buildspec when the config and
permissions layers are confirmed correct.

## Pre-flight: build state and gather-info gate

### Account-wide pre-flight commands

```bash
# 1. Build details (phases, logs, source, environment, artifacts, cache)
aws codebuild batch-get-builds \
  --ids <build-id> --output json

# 2. Project details (environment, serviceRole, source, vpcConfig,
#    cache, timeoutInMinutes, badge, batchConfig)
aws codebuild batch-get-projects \
  --names <project-name> --output json

# 3. Recent build log events
aws logs get-log-events \
  --log-group-name /aws/codebuild/<project-name> \
  --log-stream-name <build-id-stream> \
  --output json

# 4. Service role policy check
aws iam list-attached-role-policies \
  --role-name <service-role-name> --output json
aws iam list-role-policies \
  --role-name <service-role-name> --output json

# 5. AWS Health (regional CodeBuild events)
aws health describe-events \
  --filter eventStatusCodes=OPEN,UPCOMING \
  --region us-east-1 --output json
```

### Build-state short-circuit

| Build phase status | Effect on diagnosis |
|---|---|
| `phases[0].phaseType: SUBMITTED`, all phases `SUCCEEDED` | Build succeeded; if the user reports a failure, check the correct build ID. |
| `phases[].phaseStatus: FAILED` | The first `FAILED` phase is the entry point. Read `contexts[].statusCode` and `contexts[].message` for the error category. |
| `phases[].phaseStatus: TIMED_OUT` | CodeBuild killed the build at `timeoutInMinutes`. Distinguish config timeout (raise the limit) from downstream hang (fix the downstream). |
| `phases[].phaseStatus: STOPPED` | The build was manually stopped or stopped by a batch build failure. Check `buildStoppedReason`. |
| `QUEUED` phase duration > 10 minutes | Queued concurrency limit reached. Check account `CodeBuild: Concurrently executing builds` quota. |

If the input is malformed (missing project name, absent symptom
description, no build ID for live diagnosis), emit:

```text
TARGET: <project-name or unknown>
VERDICT: INSUFFICIENT_DATA
REASON: Input is missing required context — at minimum a symptom
  description (the error string, failed phase, or observed behaviour)
  and the project name or build ID.
ROOT_CAUSE: UNKNOWN
EVIDENCE:
  - Missing: <list specific missing fields>
REMEDIATION: Re-prompt the operator for: (1) the project name or build
  ID, (2) the observed symptom (error string, failed phase, timeout), and
  (3) for live diagnosis, the region and any recent project changes.
```

## Process — Diagnostic decision tree

The diagnostic tree is phase-status-driven. Find the first `FAILED`
phase and jump to that section. Each section ends with either a positive
root-cause confirmation (failing probe that matches the symptom) or a
pass that moves to the next probe.

### Step 0: Non-obvious behaviours that change diagnosis

- **CodeBuild phases are strictly sequential.** `INSTALL` runs before
  `PRE_BUILD`, which runs before `BUILD`, which runs before `POST_BUILD`,
  which runs before `UPLOAD_ARTIFACTS`. A failure in any phase prevents
  all subsequent phases. Always read the first `FAILED` phase.

- **`BUILD_CONTAINER_UNABLE_TO_PULL_IMAGE` fires during `PROVISIONING`
  or `INSTALL`.** CodeBuild pulls the environment image at the start of
  the build. If the image is in ECR and the service role lacks ECR
  permissions, the pull fails before any buildspec command runs. This
  looks like "the build never started" but is an IAM issue.

- **Docker-in-Docker requires `privilegedMode: true` at the project
  level.** The `docker` daemon is only started when `privilegedMode` is
  `true`. Without it, `docker build`, `docker push`, and even `docker
  ps` fail with "Cannot connect to the Docker daemon." This config is
  invisible in the buildspec — it is on the project's `environment`
  object.

- **VPC-attached builds use the VPC's routing table.** A build project
  with `vpcConfig` is fully inside the VPC. Private subnets need a NAT
  Gateway for external egress (npm, PyPI, Maven, Docker Hub). AWS
  services (S3, ECR, Secrets Manager) can be reached via VPC endpoints.

- **`timeoutInMinutes` caps the total build, not per-phase.** The
  default is 60 minutes. A build that consistently hits the timeout at
  the same wall-clock point is config-limited; a build that hits the
  timeout at varying points is downstream-limited.

- **S3 cache requires both the cache bucket config AND service role
  permissions.** If the project has `cache.type: S3` but the service
  role lacks `s3:GetObject` / `s3:PutObject` on the cache bucket, the
  build runs without errors but the cache is silently ignored — builds
  are slower but do not fail. Cache failures are "slow build" problems,
  not "failed build" problems.

- **Environment variables of type `SECRETS_MANAGER` or
  `PARAMETER_STORE` require service role permissions.** CodeBuild
  resolves these at build start; if the role lacks
  `secretsmanager:GetSecretValue` or `ssm:GetParameter`, the variable
  resolves to empty or the build fails in `INSTALL` with an
  "access denied" message.

- **Batch builds have their own config.** The buildspec `batch` block
  and the project's `concurrentBuildLimit` control batch behaviour. A
  batch build that fails because a single sub-build failed is NOT a
  buildspec syntax error — it is batch orchestration.

### Step 1: DOWNLOAD_SOURCE failures

Symptom: `phases[].phaseType: DOWNLOAD_SOURCE`, `phaseStatus: FAILED`.
The build cannot clone or download the source.

```bash
aws codebuild batch-get-builds --ids <build-id> --output json | \
  jq '.builds[0] | {source: .source, sourceVersion: .sourceVersion,
    resolvedSourceVersion: .resolvedSourceVersion,
    phases: [.phases[] | select(.phaseType == "DOWNLOAD_SOURCE")]}'
```

Common patterns:

| `contexts[].message` | ROOT_CAUSE |
|---|---|
| `authentication failed` for CodeCommit source | SOURCE_CHECKOUT_AUTH — the service role lacks `codecommit:GitPull` or the source credential is invalid |
| `Could not find commit` / `reference not found` | SOURCE_CHECKOUT_AUTH — the branch or commit SHA does not exist |
| `Bad credentials` for GitHub source | SOURCE_CHECKOUT_AUTH — the stored personal access token expired or was revoked |
| `rate limit exceeded` for GitHub source | SOURCE_CHECKOUT_AUTH — GitHub API rate limit; use a CodeStar connection for higher limits |
| `Access Denied` when downloading S3 source | SOURCE_CHECKOUT_AUTH — service role lacks `s3:GetObject` on the source bucket |
| `timed out` cloning large repo | BUILD_TIMEOUT_DOWNSTREAM — clone exceeds the phase timeout; use sparse checkout or shallow clone |

**Verdict:** ROOT_CAUSE_IDENTIFIED, `ROOT_CAUSE: SOURCE_CHECKOUT_AUTH`.

### Step 2: BUILD_CONTAINER_UNABLE_TO_PULL_IMAGE

Symptom: `contexts[].message` contains `BUILD_CONTAINER_UNABLE_TO_PULL_IMAGE`.

#### 2a: Check the image source

```bash
aws codebuild batch-get-projects --names <project-name> --output json | \
  jq '.projects[0].environment.image'
```

If the image is an ECR URI (`<account>.dkr.ecr.<region>.amazonaws.com/<repo>:<tag>`):

#### 2b: ECR auth check

```bash
# Service role has ECR permissions?
aws iam simulate-principal-policy \
  --policy-source-arn <service-role-arn> \
  --action-names ecr:BatchGetImage ecr:GetDownloadUrlForLayer ecr:BatchCheckLayerAvailability \
  --output json --profile <p>
```

If `implicitDeny`, **ROOT_CAUSE_IDENTIFIED** with
`ROOT_CAUSE: IMAGE_PULL_AUTH`. Fix: add ECR read permissions to the
service role.

For cross-account ECR images, also check the ECR repo policy:

```bash
aws ecr get-repository-policy --repository-name <repo> --output json --profile <p>
```

#### 2c: Image size check

```bash
aws ecr describe-images --repository-name <repo> --image-ids imageTag=<tag> \
  --output json | jq '.imageDetails[].imageSizeInBytes'
```

CodeBuild's build container has a 15 GB uncompressed Docker storage
cap. Images approaching this limit may fail to pull due to storage
exhaustion. **ROOT_CAUSE_IDENTIFIED** with `ROOT_CAUSE: IMAGE_PULL_SIZE`.

#### 2d: Docker Hub rate limit

If the image is from Docker Hub (`docker.io/<image>`), the pull may
fail due to anonymous rate limiting. Store Docker Hub credentials as a
CodeBuild source credential or use `secretsmanager` to inject
`DOCKERHUB_USERNAME` / `DOCKERHUB_TOKEN` and run `docker login` in
the `PRE_BUILD` phase.

**Verdicts:**
- Service role lacks ECR permissions: `IMAGE_PULL_AUTH`.
- Image too large: `IMAGE_PULL_SIZE`.
- Docker Hub rate limit: `IMAGE_PULL_AUTH` (credential issue).

### Step 3: INSTALL / PRE_BUILD / BUILD phase command failures

Symptom: `phases[].phaseStatus: FAILED` in a command-execution phase.
The buildspec command exited with a non-zero code.

```bash
aws codebuild batch-get-builds --ids <build-id> --output json | \
  jq '.builds[0].phases[] | select(.phaseStatus == "FAILED") | {phaseType, contexts, durationInSeconds}'

# Read the build logs for the failed phase
aws logs filter-log-events \
  --log-group-name /aws/codebuild/<project-name> \
  --log-stream-names <build-id-stream> \
  --filter-pattern '"Phase complete" OR "Command failed" OR "error"' \
  --output json
```

#### 3a: Docker build failure

If the log contains `Cannot connect to the Docker daemon` or
`docker: command not found`:

```bash
aws codebuild batch-get-projects --names <project-name> --output json | \
  jq '.projects[0].environment.privilegedMode'
```

If `privilegedMode` is `false` or absent, **ROOT_CAUSE_IDENTIFIED**
with `ROOT_CAUSE: DOCKER_PRIVILEGED_MODE`. Fix: update the project
environment to `privileged-mode: true`.

#### 3b: Package install failure

If the INSTALL or PRE_BUILD phase fails on `npm install`, `pip install`,
`mvn install`, or similar:

- Check if the build is VPC-attached without a NAT Gateway (see Step 5).
- Check if the runtime version matches the package requirements.
- Check if the package registry is reachable from the VPC.

If the failure is a genuine command error (syntax, logic, missing file),
**ROOT_CAUSE_IDENTIFIED** with `ROOT_CAUSE: PHASE_COMMAND_FAIL`. This
requires the operator to fix the buildspec command; the diagnosis should
identify the exact command and error.

#### 3c: Runtime version failure

If the INSTALL phase fails with `runtime version not available` or the
build uses a deprecated runtime:

```bash
# Check the runtime in the buildspec
# (read from the source or the project environment)
aws codebuild batch-get-projects --names <project-name> --output json | \
  jq '.projects[0].environment.image'
```

CodeBuild managed images (`aws/codebuild/<image>`) have specific runtime
versions. A removed runtime version (e.g., `nodejs: 12`, `python: 3.7`)
produces a YAML_FILE_ERROR during INSTALL.

**ROOT_CAUSE_IDENTIFIED** with `ROOT_CAUSE: RUNTIME_VERSION`. Fix:
update the buildspec `phases.install.runtime-versions` to a supported
version.

### Step 4: UPLOAD_ARTIFACTS failures

Symptom: `phases[].phaseType: UPLOAD_ARTIFACTS`, `phaseStatus: FAILED`.

#### 4a: S3 artifact permission

```bash
aws codebuild batch-get-builds --ids <build-id> --output json | \
  jq '.builds[0] | {artifacts: .artifacts, encryptionKey: .encryptionKey}'

aws codebuild batch-get-projects --names <project-name> --output json | \
  jq '.projects[0].artifacts'
```

Check the service role for S3 permissions:

```bash
aws iam simulate-principal-policy \
  --policy-source-arn <service-role-arn> \
  --action-names s3:PutObject s3:GetObject s3:ListBucket \
  --resource-arns <artifact-bucket-arn> <artifact-bucket-arn>/* \
  --output json --profile <p>
```

If `implicitDeny`, **ROOT_CAUSE_IDENTIFIED** with
`ROOT_CAUSE: ARTIFACT_S3_PERMISSION`. Fix: add S3 permissions to the
service role.

#### 4b: KMS encryption key

If the artifacts bucket uses a customer-managed KMS key:

```bash
aws iam simulate-principal-policy \
  --policy-source-arn <service-role-arn> \
  --action-names kms:Decrypt kms:GenerateDataKey \
  --resource-arns <key-arn> \
  --output json --profile <p>
```

If `implicitDeny`, **ROOT_CAUSE_IDENTIFIED** with
`ROOT_CAUSE: ARTIFACT_KMS`. Fix: add KMS permissions to the service
role for the artifacts bucket key.

#### 4c: Artifact packaging

If the error is `artifacts packaging failed` or `zip error`, the
buildspec `artifacts.files` glob may not match any files. Verify the
paths exist in the build output.

### Step 5: VPC-attached build failures

Symptom: build fails in PROVISIONING or hangs/times out in INSTALL or
PRE_BUILD when reaching external hosts.

```bash
aws codebuild batch-get-projects --names <project-name> --output json | \
  jq '.projects[0].environment.vpcConfig'
```

`vpcConfig` populated → the build is VPC-attached.

#### 5a: Route table check

```bash
aws ec2 describe-route-tables \
  --filters Name=association.subnet-id,Values=<subnet-id-1> <subnet-id-2> \
  --output json | jq '.RouteTables[].Routes'
```

For internet/package-registry egress: must have a NAT Gateway route.
For AWS services: VPC endpoints (Gateway for S3/DynamoDB, Interface for
others).

If no route exists for the destination, **ROOT_CAUSE_IDENTIFIED** with
`ROOT_CAUSE: VPC_NO_EGRESS`.

#### 5b: Security group check

```bash
aws ec2 describe-security-groups \
  --group-ids <sg-from-vpc-config> \
  --output json | jq '.SecurityGroups[].IpPermissionsEgress'
```

If the SG egress is locked down and does not allow the destination port
(typically 443 for HTTPS), **ROOT_CAUSE_IDENTIFIED** with
`ROOT_CAUSE: VPC_SG_BLOCKING`.

### Step 6: Build timeout

Symptom: `phases[].phaseStatus: TIMED_OUT`.

```bash
aws codebuild batch-get-builds --ids <build-id> --output json | \
  jq '.builds[0] | {timeoutInMinutes, buildDuration, phases: [.phases[] | {phaseType, phaseStatus, durationInSeconds}]}'
```

Distinguish:
- **Config timeout:** `timeoutInMinutes` is too low for the build's
  typical duration. The phase that was running when the timeout hit is
  consistently the same. Fix: raise `timeoutInMinutes` (1-480 minutes).
- **Downstream hang:** a command hangs on a network call (stuck
  download, unresponsive dependency, deadlocked build step). The phase
  that times out varies. Fix: investigate the downstream dependency.

### Step 7: Cache configuration issues

Symptom: builds are consistently slow; cache does not appear to work.

```bash
aws codebuild batch-get-projects --names <project-name> --output json | \
  jq '.projects[0] | {cache: .cache, environment: {privilegedMode: .environment.privilegedMode}}'
```

#### 7a: S3 cache misconfiguration

If `cache.type: S3`:
- Verify the bucket exists and the service role has `s3:GetObject` /
  `s3:PutObject` on `cache.bucket/*`.
- Without permissions, the cache is silently skipped (no error, just
  slower builds).

**ROOT_CAUSE_IDENTIFIED** with `ROOT_CAUSE: CACHE_S3_MISCONFIG`.

#### 7b: Local cache misconfiguration

If `cache.type` includes `LOCAL_DOCKER_LAYER`:
- Verify `environment.privilegedMode: true`. Local Docker layer cache
  requires privileged mode; without it, the cache is ignored.

**ROOT_CAUSE_IDENTIFIED** with `ROOT_CAUSE: CACHE_LOCAL_MISCONFIG`.

### Step 8: Environment variable / Secret resolution

Symptom: a buildspec command references an environment variable that is
empty, or the INSTALL phase fails with an access-denied message for
Secrets Manager or SSM Parameter Store.

```bash
aws codebuild batch-get-projects --names <project-name> --output json | \
  jq '.projects[0].environment.environmentVariables'
```

For `type: SECRETS_MANAGER` variables:

```bash
aws iam simulate-principal-policy \
  --policy-source-arn <service-role-arn> \
  --action-names secretsmanager:GetSecretValue \
  --resource-arns <secret-arn> \
  --output json --profile <p>
```

For `type: PARAMETER_STORE` variables:

```bash
aws iam simulate-principal-policy \
  --policy-source-arn <service-role-arn> \
  --action-names ssm:GetParameter \
  --resource-arns <parameter-arn> \
  --output json --profile <p>
```

If the role lacks permissions, **ROOT_CAUSE_IDENTIFIED** with
`ROOT_CAUSE: SECRET_ACCESS`. Fix: add the required permission to the
service role.

If the variable is `type: PLAINTEXT` and empty, check the project
config. If the variable was expected from a source like a build badge
or webhook, verify the source integration.

### Step 9: Buildspec syntax errors

Symptom: `contexts[].statusCode: YAML_FILE_ERROR` or the build fails
before any phase runs.

Validate the buildspec:

```bash
# If the buildspec is in the source, validate it
aws codebuild validate-buildspec --cli-input-yaml file://buildspec.yml --output json
```

Common syntax errors:

| Error | ROOT_CAUSE |
|---|---|
| `Phase context status code: YAML_FILE_ERROR` with a YAML parse message | BUILDSPEC_SYNTAX — indentation, tab characters, or invalid YAML structure |
| `runtime-versions` references a removed version | BUILDSPEC_SYNTAX (runtime availability) |
| `phases.build.commands` is not a list | BUILDSPEC_SYNTAX — commands must be a YAML array of strings |
| `artifacts.files` glob is invalid | BUILDSPEC_SYNTAX — artifact path glob does not match the output |
| Unknown top-level key in buildspec | BUILDSPEC_SYNTAX — only `version`, `run-as`, `env`, `proxy`, `batch`, `phases`, `reports`, `artifacts`, `cache` are valid top-level keys |

**ROOT_CAUSE_IDENTIFIED** with `ROOT_CAUSE: BUILDSPEC_SYNTAX`.

### Step 10: Queued builds and batch config

#### 10a: Queued concurrency

Symptom: builds stay in `QUEUED` for a long time.

```bash
aws codebuild batch-get-projects --names <project-name> --output json | \
  jq '.projects[0].concurrentBuildLimit'

# Check account-level quota
aws service-quotas get-service-quota \
  --service-code codebuild \
  --quota-code L-1BFC63E6 \
  --output json --profile <p>
```

If the project's `concurrentBuildLimit` or the account quota is reached,
**ROOT_CAUSE_IDENTIFIED** with `ROOT_CAUSE: QUEUED_CONCURRENCY`.

#### 10b: Batch build configuration

Symptom: batch build fails or does not fan out correctly.

```bash
# Read the buildspec batch block (from the source)
# Check the project batch config
aws codebuild batch-get-projects --names <project-name> --output json | \
  jq '.projects[0] | {batchConfiguration: .batchConfiguration}'
```

Common batch issues:
- `batch.build-graph` has circular dependencies between build graphs.
- `batch.build-list` references a buildspec that does not exist.
- `fail-fast: true` cancels all sub-builds when one fails; this is
  expected behaviour, not a config error.
- The service role lacks permissions for all sub-build artifacts.

**ROOT_CAUSE_IDENTIFIED** with `ROOT_CAUSE: BATCH_CONFIG`.

### Step 11: Build badge failures

Symptom: the build badge URL returns 404 or does not update.

```bash
aws codebuild batch-get-projects --names <project-name> --output json | \
  jq '.projects[0] | {badgeEnabled: .badgeEnabled, projectVisibility: .projectVisibility}'
```

Build badges require:
- `badgeEnabled: true` on the project.
- The project's source must support badges (CodeCommit, GitHub, S3).
- The badge URL format: `https://codebuild.<region>.amazonaws.com/badges?uuid=<project-badge-token>`

If `badgeEnabled` is false, enable it:

```bash
aws codebuild update-project --name <project-name> \
  --badge-enabled badgeEnabled=true --profile <p>
```

**ROOT_CAUSE_IDENTIFIED** with `ROOT_CAUSE: BADGE_GENERATION`.

### Step 12: INSUFFICIENT_DATA — when to bail

Emit `INSUFFICIENT_DATA` when:

- The input lacks the project name or build ID and the symptom is too
  generic to identify a category.
- A probe requires operator input (e.g., the expected runtime version
  is unknown, the buildspec is not available).
- The symptom matches no row in the quick navigation table and the
  build logs are empty or stale.
- An AWS Health event is OPEN in the region and may be the cause.

ALWAYS list the missing inputs and the exact next probe to run.

## Worked examples

### Worked example — Docker privileged mode

```text
TARGET: cb-prod-api / build-id: cb-prod-api:abc12345
VERDICT: ROOT_CAUSE_IDENTIFIED
REASON: The BUILD phase fails with "Cannot connect to the Docker daemon."
  The project's environment.privilegedMode is false. Docker-in-Docker
  builds require privilegedMode: true on the project environment (Step 3a).
ROOT_CAUSE: DOCKER_PRIVILEGED_MODE
EVIDENCE:
  - Symptom: every build fails in the BUILD phase at the "docker build"
    command with "Cannot connect to the Docker daemon."
  - Probe: aws codebuild batch-get-projects returns
    environment.privilegedMode: false.
  - Passing: the buildspec is valid YAML; the Dockerfile exists in the
    source; ECR permissions are present (image pull not the issue).
REMEDIATION:
  1. Enable privileged mode on the project:
     aws codebuild update-project --name cb-prod-api \
       --environment privilegedMode=true,... --profile <p>
  2. Verify by re-running the build; the BUILD phase should reach the
    "docker build" command without a daemon error.
CONFIRM: Before updating the project, emit and await:
  "CONFIRM: About to enable privilegedMode on cb-prod-api. Proceed?
  (yes/no)"
```

### Worked example — ECR image pull auth

```text
TARGET: cb-deploy-runner / build-id: cb-deploy-runner:def67890
VERDICT: ROOT_CAUSE_IDENTIFIED
REASON: The INSTALL phase fails with BUILD_CONTAINER_UNABLE_TO_PULL_IMAGE.
  The environment image is
  111111111111.dkr.ecr.us-east-1.amazonaws.com/base-images:latest (a
  cross-account ECR image in account 111111111111). The service role
  lacks ecr:BatchGetImage and ecr:GetDownloadUrlForLayer (Step 2b).
ROOT_CAUSE: IMAGE_PULL_AUTH
EVIDENCE:
  - Symptom: build fails in INSTALL with
    "BUILD_CONTAINER_UNABLE_TO_PULL_IMAGE: Unable to pull
    111111111111.dkr.ecr.us-east-1.amazonaws.com/base-images:latest."
  - Probe: aws iam simulate-principal-policy on the service role for
    ecr:BatchGetImage returns implicitDeny.
  - Passing: the image exists in ECR (describe-images returns
    imageSizeInBytes: 850000000, which is under the 15 GB cap); the
    build is not VPC-attached (VPC config is not a factor).
REMEDIATION:
  1. Add an inline policy to the service role granting ECR read on the
    cross-account repo:
     aws iam put-role-policy --role-name <service-role-name> \
       --policy-name ecr-pull-base-images \
       --policy-document '{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Action":["ecr:BatchGetImage","ecr:GetDownloadUrlForLayer","ecr:BatchCheckLayerAvailability"],"Resource":"arn:aws:ecr:us-east-1:111111111111:repository/base-images"}]}'
  2. Also verify the ECR repo policy in account 111111111111 grants the
    CodeBuild service role's account access.
  3. Verify by re-running the build; INSTALL should pull the image
    successfully.
CONFIRM: Before updating the role, emit and await:
  "CONFIRM: About to add ECR read permissions to the service role.
   Proceed? (yes/no)"
```

### Worked example — INSUFFICIENT_DATA

```text
TARGET: unknown
VERDICT: INSUFFICIENT_DATA
REASON: Input is "CodeBuild build failing in prod" with no project name,
  build ID, failed phase, or error string; the category cannot be
  determined.
ROOT_CAUSE: UNKNOWN
EVIDENCE:
  - Missing: project name or build ID
  - Missing: observed error string or failed phase
  - Missing: region
REMEDIATION:
  1. Run aws codebuild list-projects and share the project name.
  2. Run aws codebuild list-builds-for-project --project-name <name>
     and share the most recent build ID.
  3. Run aws codebuild batch-get-builds --ids <build-id> and share the
     phases[] output.
```

## Pre-flight safety checks

- **MANDATORY CONFIRMATION GATE.** Before any state-changing operation
  (`update-project`, `put-role-policy`, `create-vpc-endpoint`,
  `start-build`), emit and await operator approval.
- **Read-only first.** Every probe in the diagnostic tree is read-only
  (`batch-get-builds`, `batch-get-projects`, `get-log-events`,
  `simulate-principal-policy`, `describe-*`).
- **Updating a project** (`update-project`) is safe and non-disruptive
  for config-only changes; in-flight builds continue with the prior
  config. New builds pick up the updated config.
- **Changing the service role** (`put-role-policy`) affects all builds
  that use the role; verify no other projects share the role before
  narrowing permissions.
- **Enabling privileged mode** grants the build container elevated
  access. Only enable when Docker-in-Docker is required; not for all
  projects.
- **VPC config changes** trigger new ENI creation; for high-throughput
  projects, plan outside a traffic peak.
- **Bulk remediation batch limit.** When the same root cause affects
  multiple projects (e.g., a missing ECR permission after a key
  rotation), batch into groups of at most 5 projects and verify between
  batches.

## Remediation guidance

| ROOT_CAUSE | Specific fix |
|---|---|
| `IMAGE_PULL_AUTH` | Add `ecr:BatchGetImage`, `ecr:GetDownloadUrlForLayer`, `ecr:BatchCheckLayerAvailability` to the service role for the image repo; for cross-account, also update the ECR repo policy. |
| `IMAGE_PULL_SIZE` | Reduce image below 10 GB compressed (target < 1 GB); use multi-stage Docker builds; remove unnecessary layers. |
| `PHASE_COMMAND_FAIL` | Fix the buildspec command — check the error log for the exact exit code and message; verify file paths and dependencies. |
| `BUILDSPEC_SYNTAX` | Run `codebuild validate-buildspec`; fix YAML indentation (use spaces, never tabs); verify `runtime-versions` references supported versions. |
| `ENV_VAR_RESOLUTION` | Add the missing environment variable to the project config; verify `type: PLAINTEXT` values are non-empty. |
| `ARTIFACT_S3_PERMISSION` | Add `s3:PutObject`, `s3:GetObject`, `s3:ListBucket` on the artifacts bucket to the service role. |
| `ARTIFACT_KMS` | Add `kms:Decrypt`, `kms:GenerateDataKey` on the artifacts bucket's KMS key to the service role. |
| `VPC_NO_EGRESS` | Add a NAT Gateway route for external egress; or add VPC endpoints (ecr.api, ecr.dkr, s3 gateway) for AWS services. |
| `VPC_SG_BLOCKING` | Add an egress rule allowing HTTPS (443) to the package registry / destination host. |
| `RUNTIME_VERSION` | Update buildspec `phases.install.runtime-versions` to a supported version (e.g., `nodejs: 20`, `python: 3.12`). |
| `BUILD_TIMEOUT_CONFIG` | Raise `timeoutInMinutes` (1-480 minutes) via `update-project --timeout-in-minutes <n>`. |
| `BUILD_TIMEOUT_DOWNSTREAM` | Investigate the slow command (network download, stuck test); add retries or cache the download. |
| `SOURCE_CHECKOUT_AUTH` | For CodeCommit: verify the service role has `codecommit:GitPull`; for GitHub: rotate the personal access token or use a CodeStar connection. |
| `CACHE_S3_MISCONFIG` | Verify `cache.bucket` exists; add `s3:GetObject` / `s3:PutObject` on `cache.bucket/*` to the service role. |
| `CACHE_LOCAL_MISCONFIG` | Enable `privilegedMode: true` for `LOCAL_DOCKER_LAYER`; verify `cache.paths` for `LOCAL_CUSTOM_CACHE`. |
| `DOCKER_PRIVILEGED_MODE` | Update the project environment: `update-project --environment privilegedMode=true,...`. |
| `SECRET_ACCESS` | Add `secretsmanager:GetSecretValue` on the secret ARN or `ssm:GetParameter` on the parameter ARN to the service role. |
| `BADGE_GENERATION` | Enable badges: `update-project --name <n> --badge-enabled badgeEnabled=true`. |
| `QUEUED_CONCURRENCY` | Raise the project `concurrentBuildLimit` or request a Service Quota increase for the account. |
| `BATCH_CONFIG` | Fix the buildspec `batch` block; verify `build-graph` dependencies; ensure the service role has permissions for all sub-build artifacts. |

## Domain

AWS CloudOps / CodeBuild CI-CD Build Automation, Build Environment
Diagnostics, Service Role IAM, VPC Networking for Build Containers,
ECR Image Distribution, and Secrets Integration.

## AWS documentation

- **CodeBuild User Guide** — https://docs.aws.amazon.com/codebuild/latest/userguide/welcome.html
- **CodeBuild buildspec reference** — https://docs.aws.amazon.com/codebuild/latest/userguide/build-spec-ref.html
- **CodeBuild build environment** — https://docs.aws.amazon.com/codebuild/latest/userguide/build-env-ref.html
- **CodeBuild VPC support** — https://docs.aws.amazon.com/codebuild/latest/userguide/use-vpc.html
- **CodeBuild Docker builds** — https://docs.aws.amazon.com/codebuild/latest/userguide/sample-docker.html
- **CodeBuild caching** — https://docs.aws.amazon.com/codebuild/latest/userguide/build-caching.html
- **CodeBuild batch builds** — https://docs.aws.amazon.com/codebuild/latest/userguide/batch-build.html
- **CodeBuild service role** — https://docs.aws.amazon.com/codebuild/latest/userguide/setting-up.html#setting-up-service-role
- **CodeBuild environment variables** — https://docs.aws.amazon.com/codebuild/latest/userguide/build-env-ref.html#build-env.ref.env-variables
- **CodeBuild runtime versions** — https://docs.aws.amazon.com/codebuild/latest/userguide/available-runtimes.html
