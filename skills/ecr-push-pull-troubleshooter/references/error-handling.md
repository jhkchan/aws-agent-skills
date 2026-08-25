# ECR Push/Pull Troubleshooter — error handling (moved from SKILL.md

Loaded on demand — content moved verbatim from SKILL.md (progressive disclosure; nothing deleted).
## Remediation guidance — per-layer fix table (moved from SKILL.md)

| Layer | Fix |
|---|---|
| AUTH_TOKEN_EXPIRED | `aws ecr get-login-password --region <region> --profile <p> \| docker login --username AWS --password-stdin <account>.dkr.ecr.<region>.amazonaws.com`. In CI, run before every push; never cache `~/.docker/config.json` across jobs. |
| AUTH_IAM_DENIED | Add `ecr:GetAuthorizationToken` on `*` to the caller's IAM policy. Service-wide API; cannot be scoped to a repository. |
| POLICY_IAM | Add the minimum-scope action on the specific repository ARN. Push: `BatchCheckLayerAvailability`, `CompleteLayerUpload`, `InitiateLayerUpload`, `PutImage`, `UploadLayerPart`. Pull: `BatchGetImage`, `GetDownloadUrlForLayer`. |
| POLICY_REPOSITORY | Add a statement to the repository's resource-based policy listing the caller's account/ARN. Always merge with the existing policy; never overwrite without reading current state. |
| LIFECYCLE_DELETED | Re-push the image OR restore from a backup region's replica. Reorder the lifecycle policy so `keep` rules sit above `expire` rules (first-match-wins). Add tag-prefix `keep` rules for production tags. |
| IMAGE_SIZE_EXCEEDED | Multi-stage build, slimmer base image, exclude dev dependencies, or split the image. The 10 GB cap is on compressed size. |
| REPLICATION_LAG | Verify the replication rule covers source region and destination. Wait for asynchronous replication (seconds to minutes) before pulling. If the rule exists and replication stalls, check AWS Health. |
| KMS_ACCESS_DENIED | Add `kms:GenerateDataAccess` (pusher) / `kms:Decrypt` (puller) on the KMS key ARN. Verify the key policy grants the ECR service principal `kms:CreateGrant`, `kms:DescribeKey`, `kms:Decrypt`, `kms:GenerateDataAccess` for `ecr.<region>.amazonaws.com`. |
| REGISTRY_ALIAS_MISMATCH | Use the correct full URI. ECR Private: `<account>.dkr.ecr.<region>.amazonaws.com/<repo>`. ECR Public: `public.ecr.aws/<alias>/<repo>`. Authenticate to the correct registry. |
| SCAN_BLOCKING | Patch the vulnerability in the base image or dependency. If the gate must be bypassed, get security-owner sign-off (not recommended as routine). |
| TAG_IMMUTABILITY | Use a new tag (recommended for traceability) OR `aws ecr put-image-tag-mutability --repository-name <repo> --image-tag-mutability MUTABLE`. |
| MANIFEST_INVALID / ARCHITECTURE_MISMATCH | Build a multi-arch manifest (`docker buildx build --platform linux/amd64,linux/arm64 --tag <uri> --push`). For Lambda, set `Architectures: [arm64]` if the image is arm64-only. For Fargate, align the task `runtimePlatform` with the image architecture. |
| PULL_THROUGH_CACHE | Verify the rule's `ecrRepositoryPrefix` and upstream URI; verify the upstream secret in Secrets Manager is valid; re-pull to trigger the cache. |
| LAYER_DOWNLOAD_FAILED | Re-push the image (the pusher uploads only missing layers); verify with `batch-check-layer-availability`; if a service event, check AWS Health. |
| THROTTLED | Client-side retry with exponential backoff; request a Service Quotas increase for the specific API; cache `batch-get-image` results locally to reduce fan-out. |
