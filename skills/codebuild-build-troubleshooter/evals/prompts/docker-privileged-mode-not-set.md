# Eval prompt: docker-privileged-mode-not-set

Diagnose the CodeBuild build failure for the following project. Walk
the phase-status-driven diagnostic tree and emit the standard
diagnostic block (TARGET, VERDICT, REASON, ROOT_CAUSE, EVIDENCE,
REMEDIATION).

Symptom: project `cb-prod-api` fails during the BUILD phase on every
build. The buildspec runs `docker build -t app .` as the first BUILD
command; it fails with "Cannot connect to the Docker daemon at
unix:///var/run/docker.sock. Is the docker daemon running?"

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
    build:
      commands:
        - docker build -t app .
VpcConfig: (none)
Cache: (none)

Recent log pattern:
  [Container] BUILD: docker build -t app .
  Cannot connect to the Docker daemon at unix:///var/run/docker.sock.
  Is the docker daemon running?
  Phase complete: BUILD State: FAILED
```

Note that the buildspec is valid YAML and the Dockerfile exists in
the source. The project is not VPC-attached and has no cache configured.
