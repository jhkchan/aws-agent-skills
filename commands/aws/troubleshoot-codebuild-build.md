---
description: Diagnose AWS CodeBuild build failures through a phase-status-driven diagnostic tree — Docker privileged mode, ECR image pull, buildspec syntax, artifact upload, VPC egress, runtime versions, caching, and batch config. Emits ROOT_CAUSE_IDENTIFIED or INSUFFICIENT_DATA.
nl_triggers:
  - "CodeBuild build failed"
  - "BUILD_CONTAINER_UNABLE_TO_PULL_IMAGE"
  - "CodeBuild phase error"
  - "CodeBuild INSTALL failed"
  - "CodeBuild PRE_BUILD failed"
  - "CodeBuild BUILD phase failed"
  - "CodeBuild POST_BUILD failed"
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
  - "troubleshoot CodeBuild build"
  - "diagnose CodeBuild failure"
  - "CodeBuild YAML_FILE_ERROR"
routes_to: codebuild-build-troubleshooter
---

# /aws:troubleshoot-codebuild-build

Activate the `codebuild-build-troubleshooter` skill and diagnose an
AWS CodeBuild build failure through the phase-status-driven diagnostic
tree.

## What it does

Reads a symptom description (error message, failed phase, observed
behaviour) plus the project configuration, then walks the phase-status-
driven diagnostic tree to a root cause with positive evidence:

1. **Pre-flight** — project config (`batch-get-projects`), build phases
   (`batch-get-builds`), recent log events, AWS Health.
2. **Phase entry** — find the first `FAILED` phase and map to a
   diagnostic branch.
3. **Branch-specific probes** —
   - DOWNLOAD_SOURCE: source credential auth (CodeCommit IAM, GitHub
     token, S3 permissions).
   - BUILD_CONTAINER_UNABLE_TO_PULL_IMAGE: ECR auth (service role
     `ecr:BatchGetImage`), image size, Docker Hub rate limit.
   - INSTALL / PRE_BUILD / BUILD: Docker daemon (privilegedMode),
     runtime version availability, package install failures (VPC egress).
   - UPLOAD_ARTIFACTS: S3 permissions (`s3:PutObject`), KMS decrypt.
   - VPC builds: route table (NAT for external), security group egress.
   - Cache: S3 cache bucket permissions, LOCAL_DOCKER_LAYER privileged
     mode requirement.
   - Buildspec: YAML validation, runtime versions, artifact paths.
   - Queued builds: concurrentBuildLimit, account Service Quotas.
   - Batch builds: build-graph dependencies, service role permissions.
4. **Verdict** — ROOT_CAUSE_IDENTIFIED (with failing probe that matches
   the symptom) or INSUFFICIENT_DATA (missing context for diagnosis).

Emits a deterministic diagnostic block per target:

```text
TARGET: <project-name / build-id>
VERDICT: ROOT_CAUSE_IDENTIFIED | INSUFFICIENT_DATA
REASON: <1-2 sentences naming the failed phase and ROOT_CAUSE>
ROOT_CAUSE: <IMAGE_PULL_AUTH | DOCKER_PRIVILEGED_MODE | ...>
EVIDENCE:
  - <observed symptom — error string or phase behaviour>
  - <failing probe — command and output that confirms the cause>
  - <passing probes — categories ruled out>
REMEDIATION:
  1. <specific action with CLI command>
  2. <verification command after the fix>
```

## When to invoke

Paste a symptom description and ask any of:

- "CodeBuild build fails in BUILD phase"
- "BUILD_CONTAINER_UNABLE_TO_PULL_IMAGE"
- "CodeBuild Docker build — daemon not found"
- "CodeBuild artifact upload Access Denied"
- "CodeBuild npm install ETIMEDOUT in VPC"
- "CodeBuild YAML_FILE_ERROR"
- "CodeBuild queued forever"
- "CodeBuild cache not working"

A bare project name + any error verb also routes here via the
orchestrator.

## Inputs

- Symptom description: error string, failed phase, timeout vs command
  failure, intermittent vs persistent pattern.
- Project configuration: name, build ID, environment image, privileged
  mode, VPC config, service role, cache config, timeout.
- For live-account diagnosis: the skill uses `batch-get-builds`,
  `batch-get-projects`, `get-log-events`, `filter-log-events`,
  `simulate-principal-policy`, `ecr describe-images` /
  `get-repository-policy`, `ec2 describe-subnets` /
  `describe-route-tables` / `describe-security-groups`.

## Outputs

- One diagnostic block per target project/build.
- ROOT_CAUSE value from the enumerated set.
- Evidence section with the failing probe AND passing probes — never a
  verdict without positive evidence.
- Specific remediation: project config update, role policy edit, VPC
  endpoint creation, buildspec fix, or Service Quota increase.

## Related

- `/aws:pipeline` to enter the full CloudOps pipeline (this skill is
  the Phase 2 Troubleshoot specialist for CodeBuild build failures).
- `/aws:troubleshoot-codepipeline-failure` for CodePipeline orchestration
  failures that may trigger CodeBuild builds.
- `/aws:audit-codebuild-project` for configuration posture audits on
  the same project (encryption, logging, privileged mode exposure).
