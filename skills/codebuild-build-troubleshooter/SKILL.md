---
name: codebuild-build-troubleshooter
description: >-
  Diagnoses AWS CodeBuild build failures through a stopped-phase-first
  diagnostic tree: BUILD_CONTAINER_UNABLE_TO_PULL_IMAGE (ECR auth, image
  size, Docker Hub rate limit), phase-level command failures (INSTALL,
  PRE_BUILD, BUILD, POST_BUILD), buildspec.yml syntax and version errors,
  environment variable resolution (Plaintext, SecretsManager,
  SSM Parameter Store), artifact upload failures (S3 permissions, KMS
  encryption), VPC config errors (subnet, SG, NAT Gateway), runtime
  version mismatch, build timeout, source checkout failures (CodeCommit
  auth, GitHub token), caching issues (LOCAL_DOCKER_LAYER vs S3 cache),
  privileged-mode Docker builds, secret manager integration, build badge
  failures, queued builds, and batch configuration errors. Walks phase
  status, logs, and project config to a verified root cause with
  evidence-backed probes. Emits ROOT_CAUSE_IDENTIFIED or INSUFFICIENT_DATA.
version: 0.1.0
author: Jacky Chan — AWS Community Builder
license: Apache-2.0
compatibility: >-
  Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex,
  Gemini). Offline diagnosis works on supplied batch-get-builds JSON, log
  excerpts, and buildspec.yml. Live-account diagnosis uses aws codebuild
  batch-get-builds, batch-get-projects, aws logs get-log-events /
  filter-log-events, aws iam simulate-principal-policy, aws ecr
  get-repository-policy / describe-images, aws s3api get-bucket-policy,
  aws secretsmanager describe-secret, aws ssm get-parameter, aws ec2
  describe-subnets / describe-security-groups / describe-route-tables
  (AWS CLI v2, SSO or key-based credentials).
keywords:
  - CodeBuild
  - buildspec
  - BUILD_CONTAINER_UNABLE_TO_PULL_IMAGE
  - phase error
  - INSTALL phase
  - PRE_BUILD phase
  - BUILD phase
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
    Diagnosing why a CodeBuild build fails — phase command failures
    (INSTALL/PRE_BUILD/BUILD/POST_BUILD), image pull errors
    (BUILD_CONTAINER_UNABLE_TO_PULL_IMAGE), buildspec syntax errors,
    environment variable resolution failures, artifact upload errors,
    VPC-related build failures, runtime version mismatch, build timeout,
    source checkout failures (CodeCommit/GitHub), cache misconfiguration,
    Docker-in-Docker build failures (privileged mode), Secrets Manager /
    SSM Parameter Store integration errors, build badge failures, queued
    build concurrency limits, or batch build configuration errors.
  when_not_to_use: >-
    Application code debugging inside a build (use build logs and
    application tests), CodePipeline orchestration debugging (use
    codepipeline-failure-troubleshooter), ECR repository policy audits
    (use ecr-repository-auditor), IAM least-privilege audits on the
    CodeBuild service role (use iam-least-privilege-advisor), or
    steady-state project configuration audits (use codebuild-project-auditor).
  activation_triggers:
    - "CodeBuild build failed"
    - "BUILD_CONTAINER_UNABLE_TO_PULL_IMAGE"
    - "CodeBuild phase error"
    - "CodeBuild INSTALL failed"
    - "CodeBuild BUILD phase failed"
    - "CodeBuild buildspec error"
    - "CodeBuild Docker build failed"
    - "CodeBuild privileged mode"
    - "CodeBuild artifact upload failed"
    - "CodeBuild VPC build timeout"
    - "CodeBuild source checkout failed"
    - "CodeCommit clone failed"
    - "CodeBuild cache miss"
    - "CodeBuild Secrets Manager"
    - "CodeBuild runtime version"
    - "CodeBuild build timeout"
    - "CodeBuild queued build"
    - "CodeBuild batch build error"
  invocation_schema: >-
    Input: either (a) a symptom description (error message, failed phase
    name, observed build behaviour) optionally paired with the project
    name, build ID, and recent build logs, OR (b) a project name plus
    build context for live-account diagnosis. Output: a deterministic
    TARGET/VERDICT/REASON/ROOT_CAUSE/EVIDENCE/REMEDIATION block where
    VERDICT is ROOT_CAUSE_IDENTIFIED or INSUFFICIENT_DATA, and ROOT_CAUSE
    names the specific failure category.
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
  `phases[]` with `phaseType`, `phaseStatus`, and `contexts[].message`.
  The first `FAILED` phase is the entry point — not the overall build
  status. INSTALL failures differ entirely from BUILD or UPLOAD_ARTIFACTS.
- **BUILD_CONTAINER_UNABLE_TO_PULL_IMAGE is the highest-signal error
  string.** It points at ECR auth (service role missing ECR permissions),
  image size (exceeds the 15 GB storage cap), or Docker Hub rate limiting.
  Probe ECR repo policy, image size, and service role permissions first.
- **Docker-in-Docker builds require `privilegedMode: true`.** Without it,
  `docker build` returns "Cannot connect to the Docker daemon." This is
  the single most common CodeBuild Docker failure — a project environment
  config issue, not a buildspec issue.
- **VPC-attached CodeBuild follows standard VPC routing.** A build in a
  private subnet without NAT cannot reach package registries (npm, PyPI,
  Maven). AWS services need VPC endpoints or NAT.
- **Cache mode determines storage backend and permissions.**
  `LOCAL_DOCKER_LAYER` caches on-host (requires privileged mode); `S3`
  cache stores in a bucket (requires `s3:GetObject`/`s3:PutObject`).
  Mixing them up produces "cache not helping" patterns.

## Quick reference — phase-to-cause navigation table

| Failed phase / error string | Most likely ROOT_CAUSE | First probe |
|---|---|---|
| `QUEUED` long, never `IN_PROGRESS` | QUEUED_CONCURRENCY | `batch-get-projects` (concurrentBuildLimit), Service Quotas |
| `PROVISIONING` → `FAILED` | VPC_NO_EGRESS / VPC_SG_BLOCKING | `vpcConfig`, `describe-subnets`, `describe-route-tables` |
| `DOWNLOAD_SOURCE` → `FAILED` | SOURCE_CHECKOUT_AUTH | `batch-get-builds` (resolvedSourceVersion), source credential |
| `INSTALL` → `FAILED` | RUNTIME_VERSION / ENV_VAR_RESOLUTION | Phase `contexts`, buildspec `phases.install` |
| `PRE_BUILD` → `FAILED` | PHASE_COMMAND_FAIL / DOCKER_PRIVILEGED_MODE | Build logs, `environment.privileged-mode` |
| `BUILD` → `FAILED` | PHASE_COMMAND_FAIL / DOCKER_PRIVILEGED_MODE | Build logs for the BUILD phase |
| `POST_BUILD` → `FAILED` | PHASE_COMMAND_FAIL / ARTIFACT_S3_PERMISSION | Build logs, exportedEnvironmentVariables |
| `UPLOAD_ARTIFACTS` → `FAILED` | ARTIFACT_S3_PERMISSION / ARTIFACT_KMS | Service role IAM, `artifacts.location`, `encryptionKey` |
| `BUILD_CONTAINER_UNABLE_TO_PULL_IMAGE` | IMAGE_PULL_AUTH / IMAGE_PULL_SIZE | ECR repo policy, image size, service role ECR perms |
| `YAML_FILE_ERROR` / `Phase context status code` | BUILDSPEC_SYNTAX | `validate-buildspec`, buildspec YAML validation |
| Build exceeds timeout, `TIMED_OUT` | BUILD_TIMEOUT_CONFIG / BUILD_TIMEOUT_DOWNSTREAM | `timeoutInMinutes`, phase duration |
| Secrets Manager / SSM param unresolved | SECRET_ACCESS | Service role IAM for `secretsmanager:GetSecretValue` |

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

- **NEVER** recommend adding a NAT Gateway to fix a VPC-attached CodeBuild
  build without first checking for VPC endpoints. ECR interface endpoints
  (`com.amazonaws.<region>.ecr.api`, `com.amazonaws.<region>.ecr.dkr`)
  and the S3 gateway endpoint are cheaper and more secure. The NAT is
  required for external package registries (npm, PyPI), not for AWS
  services.

- **NEVER** assume `privilegedMode: false` is a buildspec field. It is a
  project-level environment config (`environment.privilegedMode`). Docker-
  in-Docker builds (running `docker build` inside buildspec commands)
  REQUIRE `privilegedMode: true`. Without it, the Docker daemon is
  unavailable and every `docker` command fails in any phase.

- **NEVER** conflate `LOCAL_DOCKER_LAYER` cache with `S3` cache.
  `LOCAL_DOCKER_LAYER` caches Docker layers on the build host (ephemeral,
  requires privileged mode). `S3` cache stores compiled artifacts /
  dependency caches in an S3 bucket (persistent, requires bucket + IAM).
  Using the wrong mode produces "cache not helping" patterns.

- **NEVER** change the runtime version in a buildspec without checking
  the CodeBuild managed image support matrix. Runtime versions are removed
  when the underlying OS or language is deprecated (e.g., `nodejs: 12`,
  `python: 3.7`). A removed runtime produces `YAML_FILE_ERROR` which looks
  like a syntax error but is actually a runtime availability issue.

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
> command returns "Cannot connect to the Docker daemon."
>
> **Cache mode determines the storage backend and permissions:**
> - `LOCAL_DOCKER_LAYER` — on-host Docker layer cache; requires
>   `privilegedMode: true`; helps only if the same build host is reused.
> - `LOCAL_SOURCE_CACHE` — on-host Git source cache.
> - `LOCAL_CUSTOM_CACHE` — on-host custom paths from buildspec `cache.paths`.
> - `S3` — persistent cache in `cache.bucket`; service role needs
>   `s3:GetObject` / `s3:PutObject` on `cache.bucket/*`.

## Configuration dependency graph

```
                      CodeBuild project
                            │
         ┌─────────────────┼──────────────────────┐
         ▼                 ▼                      ▼
    environment       source               service role
    (image,           (type:               (permissions for S3,
     privileged-      CodeCommit /          ECR, Secrets Manager,
     mode, runtime,   GitHub / S3)          SSM, CloudWatch Logs,
     computeType,                            KMS)
     envVariables,          │
     vpcConfig)             ▼                     │
         │            source credential           ▼
         │            (CodeCommit = IAM;     IAM policy
         │             GitHub = OAuth        (ecr:*, s3:*,
         │             token stored as       secretsmanager:*,
         │             CodeBuild cred)       ssm:GetParameter,
         ▼                                   logs:*, kms:Decrypt)
    buildspec.yml                               │
    (phases, artifacts,                         ▼
     cache)                                S3 bucket
         │                                 (artifacts +
         ▼                                  cache bucket)
    cache config
    (type: LOCAL_* or S3;
     if S3: bucket + path)
         │
         ▼
    vpcConfig (if set)
    (subnets, securityGroups;
     private subnet → NAT
     for external egress or
     VPC endpoints for AWS)
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

## Pre-flight: gather-info gate

```bash
# 1. Build details (phases, logs, source, environment, artifacts)
aws codebuild batch-get-builds --ids <build-id> --output json

# 2. Project details (environment, serviceRole, source, vpcConfig, cache)
aws codebuild batch-get-projects --names <project-name> --output json

# 3. Build log events
aws logs get-log-events \
  --log-group-name /aws/codebuild/<project-name> \
  --log-stream-name <stream> --output json

# 4. Service role policy check
ROLE_NAME=$(echo <role-arn> | cut -d/ -f2)
aws iam list-attached-role-policies --role-name <role-name> --output json
aws iam list-role-policies --role-name <role-name> --output json

# 5. AWS Health (regional CodeBuild events)
aws health describe-events \
  --filter eventStatusCodes=OPEN,UPCOMING --output json
```

### Build-state short-circuit

| Phase status | Effect |
|---|---|
| All `SUCCEEDED` | Build succeeded; verify the correct build ID if a failure is reported. |
| First `FAILED` phase | Entry point for diagnosis. Read `contexts[].statusCode` + `message`. |
| `TIMED_OUT` | CodeBuild killed at `timeoutInMinutes`. Distinguish config from downstream hang. |
| `STOPPED` | Manually stopped or batch failure. Check `buildStoppedReason`. |
| `QUEUED` > 10 min | Concurrency limit reached. Check `concurrentBuildLimit` + Service Quotas. |

If the input is malformed (missing project name, absent symptom), emit:

```text
TARGET: <project-name or unknown>
VERDICT: INSUFFICIENT_DATA
REASON: Input is missing required context — at minimum a symptom
  description and the project name or build ID.
ROOT_CAUSE: UNKNOWN
EVIDENCE:
  - Missing: <list specific missing fields>
REMEDIATION: Re-prompt for: (1) project name or build ID, (2) the
  observed symptom, (3) region for live diagnosis.
```

## Process — Diagnostic decision tree

Find the first `FAILED` phase and jump to that section.

### Step 1: DOWNLOAD_SOURCE failures

Symptom: `phaseType: DOWNLOAD_SOURCE`, `phaseStatus: FAILED`.

| `contexts[].message` | ROOT_CAUSE |
|---|---|
| `authentication failed` (CodeCommit) | SOURCE_CHECKOUT_AUTH — service role lacks `codecommit:GitPull` |
| `Bad credentials` (GitHub) | SOURCE_CHECKOUT_AUTH — token expired or revoked |
| `rate limit exceeded` (GitHub) | SOURCE_CHECKOUT_AUTH — use CodeStar connection |
| `Access Denied` (S3 source) | SOURCE_CHECKOUT_AUTH — service role lacks `s3:GetObject` |
| `Could not find commit` / `reference not found` | SOURCE_CHECKOUT_AUTH — branch or SHA does not exist |

**Verdict:** ROOT_CAUSE_IDENTIFIED, `ROOT_CAUSE: SOURCE_CHECKOUT_AUTH`.

### Step 2: BUILD_CONTAINER_UNABLE_TO_PULL_IMAGE

Symptom: `contexts[].message` contains `BUILD_CONTAINER_UNABLE_TO_PULL_IMAGE`.

#### 2a: ECR auth

```bash
aws iam simulate-principal-policy \
  --policy-source-arn <service-role-arn> \
  --action-names ecr:BatchGetImage ecr:GetDownloadUrlForLayer ecr:BatchCheckLayerAvailability \
  --output json --profile <p>
```

`implicitDeny` → **ROOT_CAUSE_IDENTIFIED**, `ROOT_CAUSE: IMAGE_PULL_AUTH`.

For cross-account ECR images, also check the ECR repo policy:

```bash
aws ecr get-repository-policy --repository-name <repo> --output json
```

#### 2b: Image size

```bash
aws ecr describe-images --repository-name <repo> --image-ids imageTag=<tag> \
  --output json | jq '.imageDetails[].imageSizeInBytes'
```

Images approaching 15 GB uncompressed may fail to pull. **ROOT_CAUSE_IDENTIFIED**,
`ROOT_CAUSE: IMAGE_PULL_SIZE`.

#### 2c: Docker Hub rate limit

Images from Docker Hub may hit anonymous rate limits. Store Docker Hub
credentials via Secrets Manager or a CodeBuild source credential.
**ROOT_CAUSE_IDENTIFIED**, `ROOT_CAUSE: IMAGE_PULL_AUTH`.

### Step 3: INSTALL / PRE_BUILD / BUILD phase command failures

Symptom: `phaseStatus: FAILED` in a command-execution phase.

```bash
# Read phase contexts and durations
aws codebuild batch-get-builds --ids <build-id> --output json | \
  jq '.builds[0].phases[] | select(.phaseStatus == "FAILED") | {phaseType, contexts, durationInSeconds}'

# Filter logs for errors
aws logs filter-log-events \
  --log-group-name /aws/codebuild/<project-name> \
  --log-stream-names <stream> \
  --filter-pattern '"error" OR "Error" OR "failed" OR "Cannot connect"' \
  --output json
```

#### 3a: Docker daemon error

If logs show `Cannot connect to the Docker daemon`:

```bash
aws codebuild batch-get-projects --names <project-name> --output json | \
  jq '.projects[0].environment.privilegedMode'
```

`false` or absent → **ROOT_CAUSE_IDENTIFIED**, `ROOT_CAUSE: DOCKER_PRIVILEGED_MODE`.
Fix: `update-project --environment privilegedMode=true,...`.

#### 3b: Runtime version error

If INSTALL fails with `runtime version not available` or a removed
runtime is referenced:

**ROOT_CAUSE_IDENTIFIED**, `ROOT_CAUSE: RUNTIME_VERSION`. Fix: update
buildspec `phases.install.runtime-versions` to a supported version.

#### 3c: Generic command failure

A non-zero exit code from a buildspec command. **ROOT_CAUSE_IDENTIFIED**,
`ROOT_CAUSE: PHASE_COMMAND_FAIL`. The diagnosis should identify the exact
command and error from the logs.

### Step 4: UPLOAD_ARTIFACTS failures

Symptom: `phaseType: UPLOAD_ARTIFACTS`, `phaseStatus: FAILED`.

#### 4a: S3 permission

```bash
aws iam simulate-principal-policy \
  --policy-source-arn <service-role-arn> \
  --action-names s3:PutObject s3:GetObject s3:ListBucket \
  --resource-arns <bucket-arn> <bucket-arn>/* \
  --output json --profile <p>
```

`implicitDeny` → **ROOT_CAUSE_IDENTIFIED**, `ROOT_CAUSE: ARTIFACT_S3_PERMISSION`.

#### 4b: KMS encryption

If the artifacts bucket uses a customer-managed KMS key and the role
lacks `kms:Decrypt` / `kms:GenerateDataKey`:

**ROOT_CAUSE_IDENTIFIED**, `ROOT_CAUSE: ARTIFACT_KMS`.

### Step 5: VPC-attached build failures

```bash
aws codebuild batch-get-projects --names <project-name> --output json | \
  jq '.projects[0].environment.vpcConfig'
```

#### 5a: Route table

```bash
aws ec2 describe-route-tables \
  --filters Name=association.subnet-id,Values=<subnet-1> <subnet-2> \
  --output json | jq '.RouteTables[].Routes'
```

No NAT route for external egress → **ROOT_CAUSE_IDENTIFIED**,
`ROOT_CAUSE: VPC_NO_EGRESS`.

#### 5b: Security group

```bash
aws ec2 describe-security-groups --group-ids <sg> --output json | \
  jq '.SecurityGroups[].IpPermissionsEgress'
```

Locked-down SG without HTTPS (443) egress → **ROOT_CAUSE_IDENTIFIED**,
`ROOT_CAUSE: VPC_SG_BLOCKING`.

### Step 6: Build timeout

Symptom: `phases[].phaseStatus: TIMED_OUT`.

```bash
aws codebuild batch-get-builds --ids <build-id> --output json | \
  jq '.builds[0] | {timeoutInMinutes, phases: [.phases[] | {phaseType, phaseStatus, durationInSeconds}]}'
```

- **Config timeout:** `timeoutInMinutes` too low for typical duration;
  the timed-out phase is consistently the same. Fix: raise to 1-480 min.
  `ROOT_CAUSE: BUILD_TIMEOUT_CONFIG`.
- **Downstream hang:** a command hangs on a network call; the phase that
  times out varies. Fix: investigate the downstream dependency.
  `ROOT_CAUSE: BUILD_TIMEOUT_DOWNSTREAM`.

### Step 7: Cache configuration issues

Symptom: builds consistently slow; cache does not appear to work.

```bash
aws codebuild batch-get-projects --names <project-name> --output json | \
  jq '.projects[0] | {cache: .cache, privilegedMode: .environment.privilegedMode}'
```

- `cache.type: S3` but service role lacks `s3:GetObject`/`s3:PutObject`
  on `cache.bucket/*`: **ROOT_CAUSE_IDENTIFIED**, `CACHE_S3_MISCONFIG`.
  The cache is silently skipped — no error, just slower builds.
- `cache.type` includes `LOCAL_DOCKER_LAYER` but `privilegedMode: false`:
  **ROOT_CAUSE_IDENTIFIED**, `CACHE_LOCAL_MISCONFIG`. Local Docker layer
  cache requires privileged mode.

### Step 8: Environment variable / secret resolution

Symptom: buildspec references a variable that is empty, or INSTALL fails
with access-denied for Secrets Manager / SSM.

```bash
aws codebuild batch-get-projects --names <project-name> --output json | \
  jq '.projects[0].environment.environmentVariables[] | {name, type, value}'
```

For `type: SECRETS_MANAGER` variables, verify:
```bash
aws iam simulate-principal-policy --policy-source-arn <service-role-arn> \
  --action-names secretsmanager:GetSecretValue --resource-arns <secret-arn> \
  --output json --profile <p>
```

For `type: PARAMETER_STORE` variables, verify `ssm:GetParameter`.

`implicitDeny` → **ROOT_CAUSE_IDENTIFIED**, `ROOT_CAUSE: SECRET_ACCESS`.

### Step 9: Buildspec syntax errors

Symptom: `contexts[].statusCode: YAML_FILE_ERROR`.

```bash
aws codebuild validate-buildspec --cli-input-yaml file://buildspec.yml --output json
```

| Error pattern | ROOT_CAUSE |
|---|---|
| YAML parse error (indentation, tabs) | BUILDSPEC_SYNTAX |
| `runtime-versions` references removed version | BUILDSPEC_SYNTAX |
| `phases.build.commands` not a list | BUILDSPEC_SYNTAX |
| `artifacts.files` glob matches nothing | BUILDSPEC_SYNTAX |
| Unknown top-level key | BUILDSPEC_SYNTAX |

### Step 10: Queued builds and batch config

#### 10a: Queued concurrency

```bash
aws codebuild batch-get-projects --names <project-name> --output json | \
  jq '.projects[0].concurrentBuildLimit'
aws service-quotas get-service-quota --service-code codebuild \
  --quota-code L-1BFC63E6 --output json --profile <p>
```

Limit reached → **ROOT_CAUSE_IDENTIFIED**, `QUEUED_CONCURRENCY`.

#### 10b: Batch build configuration

```bash
aws codebuild batch-get-projects --names <project-name> --output json | \
  jq '.projects[0].batchConfiguration'
```

Batch issues: circular `build-graph` deps, missing buildspec, service role
lacking sub-build artifact permissions. **ROOT_CAUSE_IDENTIFIED**,
`BATCH_CONFIG`.

### Step 11: Build badge failures

```bash
aws codebuild batch-get-projects --names <project-name> --output json | \
  jq '.projects[0] | {badgeEnabled: .badgeEnabled, projectVisibility: .projectVisibility}'
```

`badgeEnabled: false` → enable: `update-project --name <n> --badge-enabled
badgeEnabled=true`. **ROOT_CAUSE_IDENTIFIED**, `BADGE_GENERATION`.

## Worked examples

### Worked example — Docker privileged mode

```text
TARGET: cb-prod-api / build-id: cb-prod-api:abc12345
VERDICT: ROOT_CAUSE_IDENTIFIED
REASON: The BUILD phase fails with "Cannot connect to the Docker daemon."
  The project environment.privilegedMode is false. Docker-in-Docker builds
  require privilegedMode: true (Step 3a).
ROOT_CAUSE: DOCKER_PRIVILEGED_MODE
EVIDENCE:
  - Symptom: every build fails in BUILD at "docker build" with
    "Cannot connect to the Docker daemon."
  - Probe: aws codebuild batch-get-projects returns
    environment.privilegedMode: false.
  - Passing: buildspec is valid YAML; Dockerfile exists; ECR perms present.
REMEDIATION:
  1. Enable privileged mode:
     aws codebuild update-project --name cb-prod-api \
       --environment privilegedMode=true,... --profile <p>
  2. Verify by re-running the build.
CONFIRM: Before updating the project, emit and await:
  "CONFIRM: About to enable privilegedMode on cb-prod-api. Proceed?
  (yes/no)"
```

### Worked example — ECR image pull auth

```text
TARGET: cb-deploy-runner / build-id: cb-deploy-runner:def67890
VERDICT: ROOT_CAUSE_IDENTIFIED
REASON: INSTALL phase fails with BUILD_CONTAINER_UNABLE_TO_PULL_IMAGE.
  The image is
  111111111111.dkr.ecr.us-east-1.amazonaws.com/base-images:latest
  (cross-account ECR). The service role lacks ecr:BatchGetImage (Step 2b).
ROOT_CAUSE: IMAGE_PULL_AUTH
EVIDENCE:
  - Symptom: INSTALL fails with "BUILD_CONTAINER_UNABLE_TO_PULL_IMAGE:
    Unable to pull .../base-images:latest."
  - Probe: aws iam simulate-principal-policy for ecr:BatchGetImage
    returns implicitDeny.
  - Passing: image exists in ECR (850 MB, under cap); not VPC-attached.
REMEDIATION:
  1. Add ECR read policy to the service role:
     aws iam put-role-policy --role-name <role-name> \
       --policy-name ecr-pull-base-images \
       --policy-document '{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Action":["ecr:BatchGetImage","ecr:GetDownloadUrlForLayer","ecr:BatchCheckLayerAvailability"],"Resource":"arn:aws:ecr:us-east-1:111111111111:repository/base-images"}]}'
  2. Verify the ECR repo policy grants cross-account access.
  3. Re-run the build; INSTALL should pull successfully.
CONFIRM: Before updating the role, emit and await:
  "CONFIRM: About to add ECR read permissions to the service role.
   Proceed? (yes/no)"
```

### Worked example — INSUFFICIENT_DATA

```text
TARGET: unknown
VERDICT: INSUFFICIENT_DATA
REASON: Input is "CodeBuild build failing in prod" with no project name,
  build ID, failed phase, or error string.
ROOT_CAUSE: UNKNOWN
EVIDENCE:
  - Missing: project name or build ID
  - Missing: observed error string or failed phase
  - Missing: region
REMEDIATION:
  1. Run aws codebuild list-projects and share the project name.
  2. Run aws codebuild list-builds-for-project --project-name <name>
     and share the most recent build ID.
  3. Run aws codebuild batch-get-builds --ids <build-id> and share
     phases[] output.
```

## Pre-flight safety checks

- **MANDATORY CONFIRMATION GATE.** Before any state-changing operation
  (`update-project`, `put-role-policy`, `create-vpc-endpoint`,
  `start-build`), emit and await operator approval.
- **Read-only first.** Every probe is read-only (`batch-get-builds`,
  `batch-get-projects`, `get-log-events`, `simulate-principal-policy`).
- **Updating a project** (`update-project`) is safe for config-only
  changes; in-flight builds continue with prior config.
- **Changing the service role** affects all projects using it; verify
  no other projects share the role.
- **Enabling privileged mode** grants elevated access; only for Docker
  builds, not all projects.
- **VPC config changes** trigger new ENI creation; plan outside peaks.
- **Bulk remediation:** batch groups of at most 5 projects.

## Remediation guidance

| ROOT_CAUSE | Specific fix |
|---|---|
| `IMAGE_PULL_AUTH` | Add `ecr:BatchGetImage`, `ecr:GetDownloadUrlForLayer` to service role; for cross-account, also update ECR repo policy. |
| `IMAGE_PULL_SIZE` | Reduce image below 10 GB compressed; use multi-stage builds. |
| `PHASE_COMMAND_FAIL` | Fix the buildspec command; check logs for exit code and message. |
| `BUILDSPEC_SYNTAX` | Run `validate-buildspec`; fix YAML indentation; verify runtime versions. |
| `ARTIFACT_S3_PERMISSION` | Add `s3:PutObject`, `s3:GetObject`, `s3:ListBucket` on artifacts bucket. |
| `ARTIFACT_KMS` | Add `kms:Decrypt`, `kms:GenerateDataKey` on the artifacts bucket key. |
| `VPC_NO_EGRESS` | Add NAT Gateway for external egress or VPC endpoints for AWS services. |
| `VPC_SG_BLOCKING` | Add egress rule allowing HTTPS (443) to package registry. |
| `RUNTIME_VERSION` | Update `runtime-versions` to a supported version. |
| `BUILD_TIMEOUT_CONFIG` | Raise `timeoutInMinutes` (1-480 min). |
| `BUILD_TIMEOUT_DOWNSTREAM` | Investigate slow command; add retries or cache downloads. |
| `SOURCE_CHECKOUT_AUTH` | CodeCommit: verify `codecommit:GitPull`; GitHub: rotate token or use CodeStar connection. |
| `CACHE_S3_MISCONFIG` | Verify `cache.bucket`; add `s3:GetObject`/`s3:PutObject` on cache bucket. |
| `CACHE_LOCAL_MISCONFIG` | Enable `privilegedMode: true` for `LOCAL_DOCKER_LAYER`. |
| `DOCKER_PRIVILEGED_MODE` | `update-project --environment privilegedMode=true,...`. |
| `SECRET_ACCESS` | Add `secretsmanager:GetSecretValue` or `ssm:GetParameter` to service role. |
| `BADGE_GENERATION` | `update-project --name <n> --badge-enabled badgeEnabled=true`. |
| `QUEUED_CONCURRENCY` | Raise `concurrentBuildLimit` or request Service Quota increase. |
| `BATCH_CONFIG` | Fix buildspec `batch` block; verify `build-graph` deps; ensure role permissions. |

## Domain

AWS CloudOps / CodeBuild CI-CD Build Automation, Build Environment
Diagnostics, Service Role IAM, VPC Networking for Build Containers,
ECR Image Distribution, and Secrets Integration.

## AWS documentation

- CodeBuild User Guide — https://docs.aws.amazon.com/codebuild/latest/userguide/welcome.html
- Buildspec reference — https://docs.aws.amazon.com/codebuild/latest/userguide/build-spec-ref.html
- Build environment — https://docs.aws.amazon.com/codebuild/latest/userguide/build-env-ref.html
- VPC support — https://docs.aws.amazon.com/codebuild/latest/userguide/use-vpc.html
- Docker builds — https://docs.aws.amazon.com/codebuild/latest/userguide/sample-docker.html
- Caching — https://docs.aws.amazon.com/codebuild/latest/userguide/build-caching.html
- Batch builds — https://docs.aws.amazon.com/codebuild/latest/userguide/batch-build.html
- Service role — https://docs.aws.amazon.com/codebuild/latest/userguide/setting-up.html#setting-up-service-role
- Runtime versions — https://docs.aws.amazon.com/codebuild/latest/userguide/available-runtimes.html
