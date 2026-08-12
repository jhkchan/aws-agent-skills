# Eval prompt: fargate-arm64-arch-mismatch

Diagnose the Fargate image pull failure for the following task. Walk the
symptom-driven diagnostic tree and emit the standard diagnostic block
(TARGET, VERDICT, REASON, LAYER, EVIDENCE, REMEDIATION).

Symptom: Fargate task in us-east-1 stops during pull with
`CannotPullContainerError: inspect image has failed: no matching
manifest for platform linux/amd64 in the manifest list`.

```text
Registry: 111111111111.dkr.ecr.us-east-1.amazonaws.com
Repository: fargate-arm64-arch-mismatch
Tag: 2026.08
Task platform: Fargate platformVersion 1.4.0
Task runtimePlatform / cpuArchitecture: LINUX x86_64

docker manifest inspect
111111111111.dkr.ecr.us-east-1.amazonaws.com/fargate-arm64-arch-mismatch:2026.08:
  {
    "schemaVersion": 2,
    "mediaType": "application/vnd.docker.distribution.manifest.v2+json",
    "config": {"architecture": "arm64", "os": "linux"},
    "layers": [...]
  }
  Note: NOT a manifest list. Single-arch arm64 image. No linux/amd64
  variant included.

aws ecr describe-images:
  imageManifest mediaType: application/vnd.docker.distribution.manifest.v2+json
  (single manifest, not a manifest list)

aws ecs describe-tasks:
  platformVersion: "1.4.0"
  cpuArchitecture: x86_64
  lastStatus: STOPPED
  stoppedReason: "manifest unknown"

Auth token freshly issued; repository policy allows same-account pull;
image exists in describe-images.
```

Image architecture is a property of the manifest, not the tag. The tag
`2026.08` points to a single-arch arm64 image. A Fargate task on x86_64
needs a linux/amd64 variant — either a multi-arch manifest list built
with `docker buildx`, or an x86_64-only image. The host platform is set
on the task definition / Lambda config, not on the ECR tag.
