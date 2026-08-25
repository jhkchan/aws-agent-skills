# Advanced patterns - CodeBuild Build Troubleshooter

> Moved verbatim from SKILL.md for progressive disclosure (agentskills.io). Load on demand.

## NEVER rules - expanded rationale

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

