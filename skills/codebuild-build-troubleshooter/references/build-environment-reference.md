# CodeBuild Build Environment Reference Guide

Supplementary reference for the CodeBuild Build Troubleshooter skill.
Loaded on-demand when a diagnostic needs phase semantics, runtime
version matrices, VPC routing rules, cache mode comparison, or
privileged-mode requirements.

## Build phase lifecycle

CodeBuild phases run strictly sequentially. A failure in any phase
prevents all subsequent phases from executing.

| Phase | Purpose | Typical failures |
|---|---|---|
| `SUBMITTED` | Build request accepted by CodeBuild | Batch config errors |
| `QUEUED` | Waiting for capacity (concurrentBuildLimit) | Concurrency limit |
| `PROVISIONING` | Build container started, environment image pulled | VPC config, image pull |
| `DOWNLOAD_SOURCE` | Source code cloned/downloaded | Source credential auth |
| `INSTALL` | Runtime versions applied, install commands run | Runtime availability, env var resolution |
| `PRE_BUILD` | Pre-build setup commands | Package install, Docker setup |
| `BUILD` | Main build commands | Command failures, Docker daemon |
| `POST_BUILD` | Post-build commands | Packaging, tagging |
| `UPLOAD_ARTIFACTS` | Artifacts uploaded to S3 | S3 permissions, KMS |
| `FINALIZING` | Build metrics and logs finalized | Rarely fails |
| `COMPLETED` | Terminal state | — |

## Runtime version matrix (CodeBuild managed images)

CodeBuild managed images support specific runtime versions. Removed
versions produce `YAML_FILE_ERROR` during INSTALL.

| Runtime | Supported versions (2026) | Removed versions |
|---|---|---|
| Node.js | 18, 20, 22 | 8, 10, 12, 14, 16 |
| Python | 3.10, 3.11, 3.12, 3.13 | 3.7, 3.8, 3.9 |
| Java | 8 (corretto8), 11, 17, 21 | OpenJDK-only variants |
| Go | 1.19, 1.20, 1.21, 1.22 | 1.14, 1.15, 1.16, 1.17 |
| .NET | 6, 8 | 3.1, 5 |
| Ruby | 3.2, 3.3 | 2.6, 2.7, 3.0 |
| PHP | 8.1, 8.2, 8.3 | 7.x |

Always check `aws codebuild list-build-projects` and the managed image
documentation for current runtime availability.

## Docker-in-Docker requirements

| Requirement | Detail |
|---|---|
| `privilegedMode` | Must be `true` on the project environment. Project-level config, NOT a buildspec field. |
| Base image | Must include the Docker CLI (`aws/codebuild/*` images include it; custom images may not). |
| Docker socket | CodeBuild starts the Docker daemon when privileged mode is enabled; no manual socket config needed. |
| Cache | `LOCAL_DOCKER_LAYER` cache mode requires privileged mode. Without it, the cache is ignored. |

## VPC networking for CodeBuild

VPC-attached CodeBuild projects follow standard VPC routing:

| Destination | Requirement |
|---|---|
| External internet (npm, PyPI, Maven, Docker Hub) | NAT Gateway in route table (private subnet) or IGW (public subnet) |
| ECR | ECR interface endpoints (`ecr.api`, `ecr.dkr`) + S3 gateway endpoint, OR NAT |
| S3 (artifacts, cache) | S3 gateway endpoint (free) OR NAT |
| Secrets Manager | Interface VPC endpoint OR NAT |
| SSM Parameter Store | Interface VPC endpoint OR NAT |
| KMS | Interface VPC endpoint OR NAT |
| CodeCommit source | Interface VPC endpoint (`git-codecommit`) OR NAT |

The S3 gateway endpoint and DynamoDB gateway endpoint are free. All
interface endpoints have an hourly charge plus per-GB data processing.

## Cache mode comparison

| Mode | Storage | Requires privilegedMode | Persistent | Best for |
|---|---|---|---|---|
| `LOCAL_DOCKER_LAYER` | Build host (ephemeral) | Yes | No (same host only) | Docker builds with layer reuse |
| `LOCAL_SOURCE_CACHE` | Build host (ephemeral) | No | No (same host only) | Git source caching |
| `LOCAL_CUSTOM_CACHE` | Build host (ephemeral) | No | No (same host only) | Custom paths from buildspec `cache.paths` |
| `S3` | S3 bucket (persistent) | No | Yes | Dependency caches, compiled artifacts |

For `S3` cache, the service role needs `s3:GetObject` and
`s3:PutObject` on `cache.bucket/*`. Without permissions, the cache is
silently skipped — builds do not fail, but are slower.

## Service role permission matrix

| CodeBuild feature | Required IAM permissions |
|---|---|
| CloudWatch Logs | `logs:CreateLogGroup`, `logs:CreateLogStream`, `logs:PutLogEvents` |
| S3 artifacts (upload) | `s3:PutObject`, `s3:GetObject`, `s3:ListBucket` on artifacts bucket |
| S3 cache | `s3:GetObject`, `s3:PutObject` on cache bucket |
| ECR image pull | `ecr:BatchGetImage`, `ecr:GetDownloadUrlForLayer`, `ecr:BatchCheckLayerAvailability` |
| ECR image push (post-build) | Above + `ecr:InitiateLayerUpload`, `ecr:UploadLayerPart`, `ecr:CompleteLayerUpload`, `ecr:PutImage` |
| Secrets Manager env vars | `secretsmanager:GetSecretValue` on the secret ARN |
| SSM Parameter Store env vars | `ssm:GetParameter` on the parameter ARN (add `ssm:GetParameters` for lists) |
| KMS-encrypted artifacts | `kms:Decrypt`, `kms:GenerateDataKey` on the encryption key ARN |
| VPC builds | The role needs `ec2:CreateNetworkInterface`, `ec2:DescribeNetworkInterfaces`, `ec2:DeleteNetworkInterface` (usually via `AWSCodeBuildDeveloperAccess` managed policy) |
| CodeCommit source | `codecommit:GitPull` on the repository |
| Build badge | No additional permissions beyond project access |

## Artifact configuration matrix

| `artifacts.type` | `artifacts.location` | Service role needs | Packaging |
|---|---|---|---|
| `S3` | Bucket name | `s3:PutObject` on bucket + KMS if encrypted | `NONE`, `ZIP` |
| `NO_ARTIFACTS` | (none) | (none) | — |
| `S3` with secondary artifacts | Bucket name + names | `s3:PutObject` on bucket/* | Per-artifact |

## Source credential matrix

| Source type | Auth method | Stored as | Failure symptom |
|---|---|---|---|
| CodeCommit | Service role IAM (`codecommit:GitPull`) | N/A (uses service role) | `authentication failed` in DOWNLOAD_SOURCE |
| GitHub | Personal access token (PAT) | CodeBuild source credential (OAuth) | `Bad credentials` in DOWNLOAD_SOURCE |
| GitHub (CodeStar connection) | CodeStar connection ARN | Project `source.auth` field | Connection PENDING → authorize in Console |
| Bitbucket | App password / OAuth | CodeBuild source credential | `authentication failed` |
| S3 | Service role IAM (`s3:GetObject`) | N/A | `Access Denied` in DOWNLOAD_SOURCE |

## Build timeout rules

| Setting | Range | Default |
|---|---|---|
| `timeoutInMinutes` | 5-480 minutes | 60 minutes |
| Queued build timeout | 5-480 minutes | 8 hours (account quota) |

A `TIMED_OUT` phase status means CodeBuild killed the build at
`timeoutInMinutes`. Distinguish:
- **Config timeout:** the phase that timed out is consistently the same
  across builds. Fix: raise `timeoutInMinutes`.
- **Downstream hang:** the phase that times out varies. Fix: investigate
  the slow downstream dependency (network download, stuck test, etc.).
