# Example usage: codebuild-build-troubleshooter

A walkthrough showing the skill diagnosing a Docker-in-Docker build
failure caused by missing privileged mode, demonstrating the
phase-status-driven triage, the Docker privileged-mode heuristic,
the evidence-backed ROOT_CAUSE_IDENTIFIED verdict, and the
project-config root cause.

## Input (user prompt)

> Our CI build for the API service started failing yesterday. Every
> build fails in the BUILD phase with "Cannot connect to the Docker
> daemon." We haven't changed the buildspec — only updated some npm
> dependencies. Help us find the actual root cause.

```text
ProjectName: cb-prod-api
BuildId: cb-prod-api:abc12345
Environment:
  Image: aws/codebuild/amazonlinux2-x86_64-standard:5.0
  PrivilegedMode: false
  ComputeType: BUILD_GENERAL1_LARGE
Buildspec:
  version: 0.2
  phases:
    install:
      runtime-versions:
        nodejs: 20
    pre_build:
      commands:
        - echo Logging in to Amazon ECR...
        - aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin 111111111111.dkr.ecr.us-east-1.amazonaws.com
    build:
      commands:
        - docker build -t prod-api:latest .
        - docker tag prod-api:latest 111111111111.dkr.ecr.us-east-1.amazonaws.com/prod-api:latest
    post_build:
      commands:
        - docker push 111111111111.dkr.ecr.us-east-1.amazonaws.com/prod-api:latest
VpcConfig: (none)
Cache: (none)

Phase details:
  INSTALL: SUCCEEDED (nodejs: 20 applied)
  PRE_BUILD: FAILED
  BUILD: (not reached)

Recent log pattern:
  [Container] PRE_BUILD: aws ecr get-login-password --region us-east-1 | docker login ...
  Cannot connect to the Docker daemon at unix:///var/run/docker.sock.
  Is the docker daemon running?
  Phase complete: PRE_BUILD State: FAILED
```

## Skill output

```text
TARGET: cb-prod-api / build-id: cb-prod-api:abc12345
VERDICT: ROOT_CAUSE_IDENTIFIED
REASON: The PRE_BUILD phase fails at "docker login" with "Cannot connect
  to the Docker daemon." The project environment.privilegedMode is false.
  Docker-in-Docker builds (docker login, docker build, docker push)
  require privilegedMode: true on the project environment. Without it,
  the Docker daemon is not started and every docker command fails (Step 3a).
ROOT_CAUSE: DOCKER_PRIVILEGED_MODE
EVIDENCE:
  - Symptom: every build fails in PRE_BUILD at "aws ecr get-login-password
    | docker login ..." with "Cannot connect to the Docker daemon at
    unix:///var/run/docker.sock. Is the docker daemon running?"
  - Probe: aws codebuild batch-get-projects returns
    environment.privilegedMode: false.
  - Passing: the buildspec is valid YAML (INSTALL phase succeeded);
    the ECR repo exists and the service role has ECR permissions
    (the PRE_BUILD "aws ecr get-login-password" command ran without
    error before the "docker login" failed); the project is not
    VPC-attached (network is not a factor).
REMEDIATION:
  1. Enable privileged mode on the project:
     aws codebuild update-project --name cb-prod-api \
       --environment privilegedMode=true,image=aws/codebuild/amazonlinux2-x86_64-standard:5.0,computeType=BUILD_GENERAL1_LARGE \
       --profile <p>
  2. Verify by re-running the build; the PRE_BUILD "docker login"
    should succeed, and BUILD "docker build" should proceed.
CONFIRM: Before updating the project, emit and await:
  "CONFIRM: About to enable privilegedMode on cb-prod-api. Proceed?
  (yes/no)"
  Do NOT run the CLI until the operator replies yes.
```

## What the skill caught that a generic assistant misses

1. **Identified the Docker daemon as a project-config issue, not a
   buildspec issue.** A generic assistant says "check if Docker is
   installed" or "try using sudo docker." The skill recognises that
   CodeBuild's managed image already includes Docker; the issue is
   `privilegedMode: false` at the project level, which prevents the
   Docker daemon from starting.

2. **Traced to the first FAILED phase (PRE_BUILD), not the BUILD
   phase the user mentioned.** The user said "BUILD phase fails," but
   the actual first failure is in PRE_BUILD at the `docker login`
   command — the build never reaches the BUILD phase. The skill reads
   the phase statuses from `batch-get-builds` rather than trusting the
   user's description.

3. **Ruled out ECR auth and VPC networking.** The `aws ecr
   get-login-password` command (an AWS CLI call) succeeded before the
   `docker login` failed — proving the service role's ECR permissions
   are correct and the build can reach ECR. The skill uses this passing
   probe to eliminate IMAGE_PULL_AUTH and VPC_NO_EGRESS.

4. **Recommended the project-config fix, not a buildspec change.** The
   primary remediation is enabling `privilegedMode` via `update-project`.
   A generic assistant might suggest modifying the buildspec to install
   Docker or start the daemon manually — both are ineffective because
   the daemon requires kernel-level access that only privileged mode
   grants.

## Slash-command invocation

```
/aws:troubleshoot-codebuild-build
```

Or via the orchestrator:

```
/aws:pipeline
You: "diagnose why cb-prod-api fails the Docker build"
```

The orchestrator emits
`[Phase: Troubleshoot | Skills routed: codebuild-build-troubleshooter]`
and hands off to this skill for the diagnostic block.

## Live-account follow-up (optional, requires AWS CLI)

After remediating, validate the build succeeds:

```bash
# Confirm privileged mode is enabled
aws codebuild batch-get-projects --names cb-prod-api --profile default \
  --query 'projects[0].environment.privilegedMode'

# Start a new build and watch the phases
aws codebuild start-build --project-name cb-prod-api --profile default \
  --query 'build.id'
# Then poll:
aws codebuild batch-get-builds --ids <new-build-id> --profile default \
  --query 'builds[0].phases[?phaseStatus==`FAILED`]'
```

Then monitor the build's `buildStatus` for `SUCCEEDED` to confirm
the Docker build, tag, and push all complete without daemon errors.
