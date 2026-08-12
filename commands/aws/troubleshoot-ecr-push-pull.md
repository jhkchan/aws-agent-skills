---
description: Diagnoses Amazon ECR push and pull failures through a fourteen-category diagnostic tree (auth token expiry, IAM GetAuthorizationToken, repository vs IAM policy, lifecycle premature delete, image size, replication lag, KMS, registry alias, scan blocking, tag immutability, manifest, pull-through cache, architecture mismatch, layer download) — emits ROOT_CAUSE_IDENTIFIED with the specific failure layer or INSUFFICIENT_DATA.
nl_triggers:
  - "ECR push denied"
  - "ECR pull denied"
  - "docker login ECR"
  - "Your authorization token has expired"
  - "denied User is not authorized to perform ecr"
  - "ImagePullBackOff ECR"
  - "no basic auth credentials ECR"
  - "ECR lifecycle policy deleted image"
  - "tag immutability overwrite ECR"
  - "image tag cannot be overwritten"
  - "KMS.AccessDeniedException ECR"
  - "cross-region replication ECR"
  - "pull-through cache ECR"
  - "no matching manifest for platform"
  - "manifest unknown ECR"
  - "Fargate arm64 x86 ECR"
  - "troubleshoot ECR push pull"
  - "CannotPullContainerError ECR"
routes_to: ecr-push-pull-troubleshooter
---

# /aws:troubleshoot-ecr-push-pull

Activate the `ecr-push-pull-troubleshooter` skill and diagnose an
Amazon ECR push or pull failure through the fourteen-category
diagnostic tree.

## What it does

Reads a symptom description (docker / aws ecr error string, observed
behaviour, caller context) plus the repository configuration, then
walks the symptom-driven diagnostic tree to a root cause with positive
evidence:

1. **Pre-flight** — registry settings (`describe-registry`), auth
   token expiry (`get-authorization-token` decode), repository
   configuration (`describe-repositories` — mutability, scan, encryption),
   resource-based policy (`get-repository-policy`), lifecycle policy
   (`get-lifecycle-policy`), AWS Health (regional incidents).
2. **Symptom entry** — map the error to one of: auth token expired,
   auth IAM denied, IAM policy denied, repository policy denied,
   lifecycle deleted, image size exceeded, replication lag, KMS access
   denied, registry alias mismatch, scan blocking, tag immutability,
   manifest / architecture mismatch, pull-through cache, layer download
   failed, throttled.
3. **Layer-specific probes** —
   - Auth token: `get-authorization-token` decode + `expiresAt` check;
     inspect `~/.docker/config.json` cached entry.
   - Auth IAM: `iam simulate-principal-policy` for `ecr:GetAuthorizationToken`
     on `*`.
   - IAM policy: `simulate-principal-policy` for the specific `ecr:*`
     actions on the repository ARN (push vs pull action sets differ).
   - Repository policy: `get-repository-policy`; cross-account needs
     BOTH IAM AND repository policy.
   - Lifecycle: `get-lifecycle-policy` rule order (first-match-wins);
     CloudTrail `BatchDeleteImage` from the ECR service principal.
   - Image size: `docker image inspect`; compare to 10 GiB compressed.
   - Replication: `describe-registry`, `get-replication-configuration`;
     `describe-images --region <dest>`.
   - KMS: `describe-registry` encryptionConfiguration; `kms describe-key`;
     simulate `kms:GenerateDataAccess` / `kms:Decrypt`.
   - Registry alias: compare URI host (`public.ecr.aws` vs
     `<account>.dkr.ecr.<region>.amazonaws.com`); `ecr-public describe-registries`.
   - Scan blocking: `describe-image-scan-findings`; trace the
     downstream CD gate.
   - Tag immutability: `describe-repositories` `imageTagMutability`.
   - Manifest / architecture: `docker manifest inspect`;
     `describe-images` imageManifest; `ecs describe-tasks`
     `runtimePlatform`; `lambda get-function-configuration` `Architectures`.
   - Pull-through cache: `describe-pull-through-cache-rules`.
   - Layer download: `batch-check-layer-availability`.
4. **Verdict** — ROOT_CAUSE_IDENTIFIED (with failing probe that matches
   the symptom) or INSUFFICIENT_DATA (a probe requires operator input).

Emits a deterministic diagnostic block per target:

```text
TARGET: <registry-uri/repo:tag>
VERDICT: ROOT_CAUSE_IDENTIFIED | INSUFFICIENT_DATA
REASON: <1-2 sentences naming the failed layer and the failing probe>
LAYER: <AUTH_TOKEN_EXPIRED | AUTH_IAM_DENIED | POLICY_REPOSITORY |
        POLICY_IAM | LIFECYCLE_DELETED | IMAGE_SIZE_EXCEEDED |
        REPLICATION_LAG | KMS_ACCESS_DENIED | REGISTRY_ALIAS_MISMATCH |
        SCAN_BLOCKING | TAG_IMMUTABILITY | MANIFEST_INVALID |
        PULL_THROUGH_CACHE | ARCHITECTURE_MISMATCH |
        LAYER_DOWNLOAD_FAILED | THROTTLED | UNKNOWN>
EVIDENCE:
  - <observed symptom — error string or behaviour>
  - <failing probe — command and its output that confirms the cause>
  - <passing probes — layers ruled out>
REMEDIATION:
  1. <specific action with CLI command>
  2. <verification command after the fix>
```

## When to invoke

Paste a symptom description and ask any of:

- "docker push returns 'Your authorization token has expired'"
- "ECS task CannotPullContainerError from ECR"
- "docker push denied — User is not authorized to perform ecr:PutImage"
- "ECR lifecycle policy deleted my production image"
- "cross-account ECR pull denied even though IAM allows it"
- "image tag already exists and is immutable"
- "Fargate task — no matching manifest for platform linux/amd64"
- "KMS.AccessDeniedException on docker push to ECR"

A bare repository URI + any error verb ("ECR failing", "push times
out", "ImagePullBackOff") also routes here via the orchestrator.

## Inputs

- Symptom description: error string, observed behaviour, intermittent
  vs persistent pattern, caller (CI bot / ECS task / Lambda /
  developer machine).
- Repository context: full registry URI (account, region, repository
  name, tag), image source account vs caller account (for cross-account
  cases).
- For live-account diagnosis: caller IAM principal, the failing
  operation (push or pull). The skill uses `get-authorization-token`,
  `describe-repositories`, `get-repository-policy`, `get-lifecycle-policy`,
  `describe-registry`, `get-replication-configuration`,
  `describe-image-scan-findings`, `batch-get-image`,
  `batch-check-layer-availability`, `kms describe-key`,
  `iam simulate-principal-policy`, `cloudtrail lookup-events`,
  `ecs describe-tasks`, `lambda get-function-configuration`.

## Outputs

- One diagnostic block per target repository/tag.
- Layer-specific LAYER value from the enumerated set.
- Evidence section with the failing probe AND passing probes (layers
  ruled out) — never a verdict without positive evidence.
- Specific remediation: token refresh, IAM policy edit, repository
  policy add, lifecycle reorder, image rebuild, KMS permission grant,
  multi-arch manifest build, or AWS Support escalation.

## Related

- `/aws:pipeline` to enter the full CloudOps pipeline (this skill is
  the Phase 2 Troubleshoot specialist for ECR push/pull failures).
- `/aws:audit-ecr-repository` for configuration posture audits on the
  same repository (lifecycle policy coverage, scan-on-push, tag
  immutability, encryption).
- `/aws:troubleshoot-iam-permission` for deeper diagnosis when the ECR
  denial traces to an SCP, permissions boundary, or session policy.
