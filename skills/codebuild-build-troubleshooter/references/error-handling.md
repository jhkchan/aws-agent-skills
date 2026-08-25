# Error handling - CodeBuild Build Troubleshooter

> Moved verbatim from SKILL.md for progressive disclosure (agentskills.io). Load on demand.

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

