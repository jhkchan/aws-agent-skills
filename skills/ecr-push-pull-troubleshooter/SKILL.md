---
name: ecr-push-pull-troubleshooter
description: 'Diagnoses Amazon ECR push and pull failures through a fourteen-category diagnostic tree: authentication (docker login token expiry, IAM ecr:GetAuthorizationToken), repository policy vs IAM policy precedence, lifecycle policy prematurely deleting images, image size limit (10 GB), cross-region replication lag, KMS encryption key access denied, registry alias confusion (public vs private), scan-on-push findings blocking deployment, image tag immutability conflicts, docker manifest errors, pull-through cache misconfiguration, Fargate/ECS platform version vs image architecture mismatch (arm64 vs x86_64), layer download failures, and throttling. Walks symptoms to a verified root cause with evidence-backed probes; emits ROOT_CAUSE_IDENTIFIED or INSUFFICIENT_DATA.'
license: Apache-2.0
compatibility: Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). Offline symptom classification works from pasted docker / aws ecr error output. Live-account diagnosis uses aws ecr
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: 'true'
  phase: '2'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: DevTools
  task_type: troubleshoot
  skill_class: capability
  lifecycle_status: active
  verdict_shape: ROOT_CAUSE_IDENTIFIED | INSUFFICIENT_DATA
  when_to_use: 'Diagnosing an ECR push or pull failure (docker login "denied: Your authorization token has expired", docker push "denied: User is not authorized", image tag overwrite rejected, image'
  when_not_to_use: Authoring a new lifecycle or repository policy from scratch (use ecr-repository-auditor), CI/CD pipeline construction (use the codepipeline / codebuild deployer skills), auditing image CVE
  activation_triggers: ''
  invocation_schema: '''Input: either (a) a symptom description (docker / aws ecr error string, observed behaviour, "push started failing after the role change"), optionally paired with the registry / repository'
  invocation_example: '"# Minimal valid input (offline symptom classification):\nSymptom: \"docker push\n  111111111111.dkr.ecr.us-east-1.amazonaws.com/app:v1 returns\\n\\\"denied: Your authorization token has\'
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  keywords: ECR, docker login, authorization token, ecr:GetAuthorizationToken, repository policy, lifecycle policy, tag immutability, image size limit, cross-region replication, KMS encryption, registry alias, public registry, scan on push, manifest, pull-through cache, Fargate architecture, arm64, x86_64, layer download, troubleshoot
---

# ECR Push/Pull Troubleshooter

## Quick start

- **Symptom → layer map (first plausible match drives the first probe):**
  `Your authorization token has expired` / `no basic auth credentials` →
  AUTH_TOKEN_EXPIRED; `is not authorized to perform ecr:` → AUTH_IAM_DENIED
  or POLICY_IAM / POLICY_REPOSITORY; image gone after a policy run →
  LIFECYCLE_DELETED; push rejected at > 10 GB → IMAGE_SIZE_EXCEEDED;
  replica missing in the far region → REPLICATION_LAG; `KMS.AccessDeniedException`
  on push → KMS_ACCESS_DENIED; pull from ECR Public when a private repo
  was intended (or vice-versa) → REGISTRY_ALIAS_MISMATCH; deploy blocked
  by scan finding → SCAN_BLOCKING; `cannot overwrite` / `image is
  immutable` → TAG_IMMUTABILITY; `manifest unknown` / `no matching
  manifest for platform` → MANIFEST_INVALID or ARCHITECTURE_MISMATCH;
  upstream registry unreachable from pull-through cache → PULL_THROUGH_CACHE;
  `Failed to register layer: layer not found` → LAYER_DOWNLOAD_FAILED.
- **Always verify with a probe, never guess.** Each layer has a single
  command that proves or disproves it. A ROOT_CAUSE_IDENTIFIED verdict
  requires positive evidence — a failing probe that matches the symptom
  — not a process of elimination.
- **The ECR auth token is base64(username:password) and valid for 12
  hours.** `aws ecr get-login-password` returns the password; `docker
  login` wraps it as base64(`AWS`:`<password>`). A push that worked an
  hour ago and now fails with `Your authorization token has expired` is
  almost always a stale token. Re-run `aws ecr get-login-password |
  docker login` and retry before investigating IAM.
- **Repository policy and IAM policy are evaluated together — BOTH must
  allow the action.** A same-account pull succeeds when the IAM principal
  has the needed actions in IAM and no repository policy is attached
  (no explicit deny). A cross-account pull requires BOTH the caller's
  IAM policy AND the repository policy to allow the caller's account.
  Adding only the IAM side is the most common cross-account ECR failure.
- **Lifecycle policy rules evaluate in order; the FIRST matching rule
  wins.** A rule "count=1, untagged=true" placed ABOVE a "count=10,
  tagged=true" rule deletes the 11th image even if you expected the
  tagged rule to protect it. Always read rule order, not just rules.
- **Tag immutability is per-repository, not per-registry.** Enabling
  `IMMUTABLE` on one repository does not affect any other. A push that
  fails with `image tag already exists` fails only on repositories
  configured as IMMUTABLE.

## Mindset
Mindset reasoning moved to
[references/advanced-patterns.md](references/advanced-patterns.md).

## Philosophy
Philosophy behaviours moved to
[references/advanced-patterns.md](references/advanced-patterns.md).

## Quick reference — symptom triage table

| Symptom phrase / error | Most likely layer | First probe |
|---|---|---|
| `Your authorization token has expired`, `no basic auth credentials` | AUTH_TOKEN_EXPIRED | `aws ecr get-authorization-token` (decode base64, check `expiresAt`); inspect `~/.docker/config.json` |
| `denied: User arn:... is not authorized to perform: ecr:GetAuthorizationToken` | AUTH_IAM_DENIED | `iam simulate-principal-policy` with `ecr:GetAuthorizationToken` on `*` |
| `denied: ... not authorized to perform: ecr:BatchCheckLayerAvailability` / `BatchGetImage` / `PutImage` | POLICY_IAM or POLICY_REPOSITORY | `get-repository-policy`, `iam simulate-principal-policy` on the repository ARN |
| Image tag was present yesterday; now `manifest unknown` and gone from `describe-images` | LIFECYCLE_DELETED | `get-lifecycle-policy`, `describe-images` for last-pushed time |
| Push fails with `Requested image size exceeds max size` | IMAGE_SIZE_EXCEEDED | `docker image inspect` Size; compare to 10 GiB compressed |
| Replica missing in far region after a push | REPLICATION_LAG | `ecr describe-registry`, `ecr get-replication-configuration`, `describe-images --region <far>` |
| `KMS.AccessDeniedException` on push or pull | KMS_ACCESS_DENIED | `describe-registry` encryptionConfiguration; `kms describe-key`; simulate `kms:GenerateDataAccess` / `kms:Decrypt` |
| `manifest unknown` but only from some callers | REGISTRY_ALIAS_MISMATCH | Compare URI host (`public.ecr.aws` vs `<account>.dkr.ecr.<region>.amazonaws.com`); alias owner |
| Deploy blocked; `describe-image-scan-findings` shows `HIGH`/`CRITICAL` | SCAN_BLOCKING | `describe-image-scan-findings`; trace the consuming CD/CodeDeploy gate |
| `image tag already exists` / `cannot be overwritten because the repository is immutable` | TAG_IMMUTABILITY | `describe-repositories` `imageTagMutability` for the repository |
| `manifest unknown`, `no matching manifest for platform linux/arm64` | MANIFEST_INVALID / ARCHITECTURE_MISMATCH | `docker manifest inspect <uri>`, `describe-images` imageManifest |
| Pull-through cache: pull loops / image never cached | PULL_THROUGH_CACHE | `describe-pull-through-cache-rules`, `describe-registry` |
| `Failed to register layer: layer does not exist` / `download failed after attempt=5` | LAYER_DOWNLOAD_FAILED | `batch-check-layer-availability`; retry on the failing region |
| `ThrottlingException: Rate exceeded` on `BatchGetImage` | THROTTLED | ECR API throttle metrics; client-side retry |

## Pre-flight: registry and gather-info gate

### Account-wide pre-flight commands
Account-wide pre-flight command block moved to
[references/diagnostic-commands.md](references/diagnostic-commands.md).


### Repository-state short-circuit
Repository-state short-circuit table moved to
[references/diagnostic-commands.md](references/diagnostic-commands.md).

If the input is malformed (missing registry URI or repository name, no
symptom description, no caller context for cross-account diagnosis),
emit:

INSUFFICIENT_DATA re-prompt template for malformed/missing input: [references/worked-examples.md](references/worked-examples.md).

## Process — Diagnostic decision tree (apply in symptom order)

The tree is symptom-driven. Pick the entry point based on the observed
symptom, then walk the layer-specific probes in order. **Never emit
ROOT_CAUSE_IDENTIFIED without a failing probe that matches the symptom.**

### Step 0: Non-obvious behaviours that change diagnosis
Step 0 non-obvious behaviours moved to
[references/advanced-patterns.md](references/advanced-patterns.md).

### Step 1: Symptom entry

| Symptom | Branch |
|---|---|
| `Your authorization token has expired`, `no basic auth credentials` | Step 2 — Auth token |
| `denied: ... is not authorized to perform: ecr:GetAuthorizationToken` | Step 3 — Auth IAM |
| `denied: ... is not authorized to perform: ecr:BatchGetImage` / `PutImage` / etc. | Step 4 + Step 5 — IAM / repository policy |
| Image gone after a lifecycle policy run; `manifest unknown` recent | Step 6 — Lifecycle |
| Push rejected with size limit | Step 7a — Image size |
| Replica missing in the far region | Step 8 — Replication |
| `KMS.AccessDeniedException` on push or pull | Step 9 — KMS |
| `manifest unknown` only from some callers; pull from ECR Public when private was intended | Step 10 — Registry alias |
| Deploy pipeline blocked; scan findings HIGH/CRITICAL | Step 11 — Scan |
| `image tag already exists`, `cannot be overwritten ... immutable` | Step 12 — Tag immutability |
| `manifest unknown`, `no matching manifest for platform` | Step 13 — Manifest / architecture |
| Pull-through cache: pull loops, upstream unreachable | Step 14 — Pull-through cache |
| `Failed to register layer: layer does not exist` | Step 15 — Layer download |

### Step 2: AUTH_TOKEN_EXPIRED — docker login token expired

Symptom: `Your authorization token has expired. Reauthenticate at ...`,
`no basic auth credentials`, `error retrieving credentials`.

Probe (token expiry via get-authorization-token, cached docker auth): [references/diagnostic-commands.md](references/diagnostic-commands.md).

The decoded token's password contains an `X-amz-expires=43200` (12-hour)
query parameter. If `expiresAt` is in the past, the cached credentials
are stale. If the token has expired, **ROOT_CAUSE_IDENTIFIED** with
`LAYER: AUTH_TOKEN_EXPIRED`. Fix: refresh the token immediately before
every push; do not cache credentials across jobs.

### Step 3: AUTH_IAM_DENIED — missing ecr:GetAuthorizationToken

Symptom: `denied: ... is not authorized to perform:
ecr:GetAuthorizationToken`. Without this permission, the caller cannot
retrieve an auth token at all.

Probe (simulate ecr:GetAuthorizationToken on `*`): [references/diagnostic-commands.md](references/diagnostic-commands.md).

`ecr:GetAuthorizationToken` must be allowed on `*` (it is a
service-wide API, not per-resource). If the simulation returns
`implicitDeny`, **ROOT_CAUSE_IDENTIFIED** with `LAYER: AUTH_IAM_DENIED`.
Fix: add `{"Effect": "Allow", "Action": "ecr:GetAuthorizationToken",
"Resource": "*"}`.

### Step 4: POLICY_IAM — IAM identity-based policy missing

Symptom: `denied: ... is not authorized to perform:
ecr:BatchCheckLayerAvailability` (or `BatchGetImage`, `PutImage`,
`CompleteLayerUpload`, `InitiateLayerUpload`, `UploadLayerPart`,
`GetDownloadUrlForLayer`).

Probe (simulate push/pull ecr actions on the repository ARN): [references/diagnostic-commands.md](references/diagnostic-commands.md).

A **push** needs at minimum: `BatchCheckLayerAvailability`,
`CompleteLayerUpload`, `InitiateLayerUpload`, `PutImage`,
`UploadLayerPart`, plus `GetAuthorizationToken`. A **pull** needs at
minimum: `BatchGetImage`, `GetDownloadUrlForLayer`, plus
`GetAuthorizationToken`. If any required action returns `implicitDeny`,
**ROOT_CAUSE_IDENTIFIED** with `LAYER: POLICY_IAM`. Add the missing
action on the specific repository ARN.

### Step 5: POLICY_REPOSITORY — repository policy missing (cross-account)

Symptom: same-account access works; cross-account pull/push is denied
even though the caller's IAM policy allows it.

Probe (get-repository-policy): [references/diagnostic-commands.md](references/diagnostic-commands.md).

Same-account callers do NOT need a repository policy — IAM alone is
sufficient. Cross-account callers need BOTH the caller's IAM policy
AND a repository policy statement listing the caller's account or ARN.
If the policy is empty or does not list the caller's
`aws:PrincipalAccount`, **ROOT_CAUSE_IDENTIFIED** with
`LAYER: POLICY_REPOSITORY`. Fix:

Fix command (set-repository-policy cross-account allow): [references/diagnostic-commands.md](references/diagnostic-commands.md).

Always confirm before changing a resource-based policy — a too-broad
principal can leak the repository.

### Step 6: LIFECYCLE_DELETED — lifecycle policy deleted the image

Symptom: image tag was present yesterday; today `manifest unknown` and
gone from `describe-images`. The operator did not delete it manually.

Probes (lifecycle policy, image list, CloudTrail BatchDeleteImage): [references/diagnostic-commands.md](references/diagnostic-commands.md).

Lifecycle rules evaluate in order, first-match-wins. Look for a rule
with `type: expire` whose `selection` matches the missing image (e.g.,
`count: 1, tagStatus: untagged` deletes any image that lost its last
tag). If a rule's `lastEvaluatedAt` matches the disappearance window
and the rule's `selection` matches, **ROOT_CAUSE_IDENTIFIED** with
`LAYER: LIFECYCLE_DELETED`. Fix: reorder the rules (place `keep` above
`expire`) or adjust `count` / `tagStatus`.

### Step 7: IMAGE_SIZE_EXCEEDED — image larger than 10 GB

Symptom: push fails with `Requested image size exceeds max size limit`
or LayerUpload fails on a single layer > 10 GB. ECR caps each
compressed layer at 10 GB and the overall compressed image at 10 GB.

```bash
docker image inspect <image>:<tag> --format '{{.Size}}'
```

Docker reports uncompressed size; the 10 GB cap is on compressed size.
For a rough check, compare docker's size to the threshold with a 1.5-2x
margin. If compressed image exceeds 10 GB, **ROOT_CAUSE_IDENTIFIED**
with `LAYER: IMAGE_SIZE_EXCEEDED`. Fix: multi-stage build, slimmer base
image, exclude dev dependencies, or split the image.

### Step 8: REPLICATION_LAG — cross-region replication delay or misconfiguration

Symptom: image pushed to source region; replica missing in destination
region. Pull in destination region fails with `manifest unknown`.

Probes (describe-registry, replication configuration, destination-region images): [references/diagnostic-commands.md](references/diagnostic-commands.md).

Replication rules are per-source-registry. If no rule covers the
repository's region and destination, no replication occurs. If a rule
exists, replication is asynchronous — typically seconds to minutes. If
no rule covers the destination, **ROOT_CAUSE_IDENTIFIED** with
`LAYER: REPLICATION_LAG`. If the rule exists but the image is missing
minutes after push, check AWS Health for replication service degradation.

### Step 9: KMS_ACCESS_DENIED — KMS encryption key access denied

Symptom: `KMS.AccessDeniedException` on push or pull when the
repository uses `encryptionType: KMS`.

Probes (encryption config, kms describe-key, simulate kms actions): [references/diagnostic-commands.md](references/diagnostic-commands.md).

The pusher needs `kms:GenerateDataAccess`; the puller needs
`kms:Decrypt`. The key policy must also grant the ECR service principal
access (typically `kms:CreateGrant` to `ecr.<region>.amazonaws.com`).
If the simulation returns `implicitDeny`, **ROOT_CAUSE_IDENTIFIED**
with `LAYER: KMS_ACCESS_DENIED`. Fix: add the KMS permissions to the
caller's IAM policy AND verify the key policy grants ECR access.

### Step 10: REGISTRY_ALIAS_MISMATCH — public vs private registry confusion

Symptom: `manifest unknown` from some callers but not others; push
appears to succeed but the image is in a different registry.

Probe (ecr-public describe-registries alias ownership): [references/diagnostic-commands.md](references/diagnostic-commands.md).

If the URI host is `public.ecr.aws` but the operator intended a
private registry (or vice-versa), or the public alias is owned by a
different account, **ROOT_CAUSE_IDENTIFIED** with
`LAYER: REGISTRY_ALIAS_MISMATCH`. Fix: use the correct full URI and
authenticate to the correct registry.

### Step 11: SCAN_BLOCKING — scan findings block deploy

Symptom: docker push succeeds; the deploy pipeline refuses to promote
the image. The gate reads `describe-image-scan-findings` and blocks on
`HIGH` / `CRITICAL`.

Probe (describe-image-scan-findings HIGH/CRITICAL): [references/diagnostic-commands.md](references/diagnostic-commands.md).

ECR does NOT block pushes based on scan findings — a downstream gate
(CodeDeploy, a Lambda promotion step, a custom security gate) does the
blocking. If scan findings are the blocker, **ROOT_CAUSE_IDENTIFIED**
with `LAYER: SCAN_BLOCKING`. Surface the findings; do NOT recommend
bypassing without a security owner.

### Step 12: TAG_IMMUTABILITY — image tag overwrite rejected

Symptom: push fails with `image tag already exists and is immutable`.

Probe (imageTagMutability check): [references/diagnostic-commands.md](references/diagnostic-commands.md).

`IMMUTABLE` blocks overwrites on the named repository only —
immutability is per-repository, not per-registry. Fix: use a new tag
(recommended for traceability) or switch to MUTABLE:

Fix command (put-image-tag-mutability MUTABLE): [references/diagnostic-commands.md](references/diagnostic-commands.md).

If the repository is `IMMUTABLE` and the push is an overwrite,
**ROOT_CAUSE_IDENTIFIED** with `LAYER: TAG_IMMUTABILITY`.

### Step 13: MANIFEST_INVALID / ARCHITECTURE_MISMATCH — manifest and architecture issues

Symptom: `manifest unknown`, `no matching manifest for platform
linux/arm64 in the manifest list`, Fargate task stops with
`CannotPullContainerError`.

Probes (docker manifest inspect, batch-get-image manifest, Fargate/Lambda platform): [references/diagnostic-commands.md](references/diagnostic-commands.md).

Manifest/architecture pattern table: [references/diagnostic-commands.md](references/diagnostic-commands.md).

If the manifest list does not include the requested platform or the
image is single-arch on the wrong host, **ROOT_CAUSE_IDENTIFIED** with
`LAYER: ARCHITECTURE_MISMATCH` (preferred) or `LAYER: MANIFEST_INVALID`
when the manifest is malformed.

### Step 14: PULL_THROUGH_CACHE — pull-through cache misconfiguration

Symptom: pull from a pull-through cache repository loops indefinitely;
upstream registry unreachable; pull fails with `upstream repository
does not exist`.

Probe (describe-pull-through-cache-rules): [references/diagnostic-commands.md](references/diagnostic-commands.md).

Pull-through-cache pattern table: [references/diagnostic-commands.md](references/diagnostic-commands.md).

If the rule is misconfigured or the upstream is unreachable,
**ROOT_CAUSE_IDENTIFIED** with `LAYER: PULL_THROUGH_CACHE`.

### Step 15: LAYER_DOWNLOAD_FAILED — layer download failures

Symptom: `failed to register layer: layer does not exist`,
`download failed after attempt=5`, retryable errors during `docker
pull` for specific layers.

Probe (batch-check-layer-availability): [references/diagnostic-commands.md](references/diagnostic-commands.md).

A layer returning `INVALID_LAYER_DIGEST` or missing from the registry
is the smoking gun. Common causes: partial upload (pusher crashed
mid-`CompleteLayerUpload`), lifecycle policy that deleted layers but
not the manifest, or a transient regional issue. If the layer is
unavailable, **ROOT_CAUSE_IDENTIFIED** with
`LAYER: LAYER_DOWNLOAD_FAILED`. Fix: re-push the image (the pusher
uploads missing layers); if the cause is a service event, check AWS
Health.

### Step 16: THROTTLED or INSUFFICIENT_DATA

If `ThrottlingException: Rate exceeded` appears on ECR APIs, route to
`LAYER: THROTTLED` — the caller is hitting the ECR API throughput
limit. Recommend client-side retry with exponential backoff and
request a Service Quotas increase for the specific API.

If none of the above produced a positive root-cause match, emit
`VERDICT: INSUFFICIENT_DATA` with the missing probe listed.

## Output format

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
CONFIRM: Before executing any state-changing CLI, emit and await operator
  approval: "CONFIRM: About to <action> on <repo> in <region>. Proceed?
  (yes/no)"
```

### Worked example — AUTH_TOKEN_EXPIRED in CI

```text
TARGET: 111111111111.dkr.ecr.us-east-1.amazonaws.com/app:v1
VERDICT: ROOT_CAUSE_IDENTIFIED
REASON: CI cached an auth token whose 12-hour expiry elapsed 2 hours ago;
  the cached entry points at a token issued 14 hours ago. The freshly
  issued token returns expiresAt = +12 hours (Step 2).
LAYER: AUTH_TOKEN_EXPIRED
EVIDENCE:
  - Symptom: docker push returns "Your authorization token has expired"
    on every push from the CI runner.
  - Probe: aws ecr get-authorization-token returned expiresAt =
    <14-hours-ago> for the cached token; the freshly-issued token
    returns expiresAt = <+12 hours>.
  - Probe: cat ~/.docker/config.json shows auths entry with the old token.
  - Passing: iam simulate-principal-policy on the CI role returns allowed
    for ecr:GetAuthorizationToken, ecr:PutImage, ecr:CompleteLayerUpload
    (policy is not the issue).
REMEDIATION:
  1. aws ecr get-login-password --region us-east-1 --profile ci-profile | \
       docker login --username AWS --password-stdin \
       111111111111.dkr.ecr.us-east-1.amazonaws.com
  2. Remove the cross-job cache for ~/.docker/config.json.
  3. Re-run the push; it should succeed in under a minute.
```

### Worked example — LIFECYCLE_DELETED
Full worked example moved to
[references/worked-examples.md](references/worked-examples.md).

## Anti-Patterns — NEVER

- NEVER declare ROOT_CAUSE_IDENTIFIED without a failing probe that
  matches the symptom.
- NEVER recommend refreshing the docker login token as the only fix
  without checking the token's actual expiry via `expiresAt`. Guessing
  "must be expired" misses IAM / repository-policy causes.
- NEVER assume a same-account pull needs a repository policy. The
  default is IAM-only for same-account; adding a repository policy to
  "fix" a same-account pull indicates the diagnosis went down the
  wrong path.
- NEVER assume a cross-account pull works with only the caller's IAM
  policy. BOTH the IAM policy AND the repository's resource-based
  policy must allow the action.
- NEVER conclude a lifecycle policy "didn't delete my image" without
  reading rule order — first-match-wins; a broad `expire` above a
  narrow `keep` deletes what `keep` would have protected.
- NEVER assume tag immutability is per-registry. It is per-repository.
- NEVER chase KMS permissions for an `AES256`-encrypted repository.
  Only `encryptionType: KMS` requires caller-side KMS permissions.
- NEVER assume scan findings block the push. ECR accepts the image
  regardless; a downstream gate does the blocking.
- NEVER recommend disabling tag immutability without flagging the
  traceability trade-off — MUTABLE lets a tag float, defeating
  reproducibility.
- NEVER assume `manifest unknown` means the image is missing. For
  multi-arch images, it can mean the manifest list does not include
  the requested platform.
- NEVER recommend a Fargate platform version change without confirming
  architecture — x86_64 vs arm64 is set on the task definition / Lambda
  config, not the platform version.
- NEVER delete an ECR image tag that a Lambda function or ECS task
  references. ECR does not track consumers; the tag breaks the next
  cold start or task rollout.
- NEVER conflate ECR Public with ECR Private. `public.ecr.aws` is a
  globally public registry; `<account>.dkr.ecr.<region>.amazonaws.com`
  is private. A login to one is not a login to the other.

## Pre-flight safety checks (run before any state-changing CLI)

- **MANDATORY CONFIRMATION GATE.** Before any state-changing operation
  (`set-repository-policy`, `put-image-tag-mutability`,
  `start-lifecycle-policy-preview`, `delete-repository`,
  `put-replication-configuration`, `delete-pull-through-cache-rule`),
  emit and await operator approval.
- **Read-only first.** Every probe is read-only (`describe-*`, `get-*`,
  `simulate-principal-policy`, `lookup-events`,
  `batch-check-layer-availability`). Do not perform state-changing
  operations as diagnostic probes.
- **`set-repository-policy`** replaces the entire resource-based policy
  — always read the current policy and merge; never overwrite. A
  too-broad principal leak is a common security incident.
- **`put-replication-configuration`** is regional and applies to the
  whole source registry — confirm scope before applying.
- **`delete-repository`** is irreversible and deletes every image —
  confirm twice; consider a lifecycle retain-window first.
- **Bulk remediation batch limit.** Batch into groups of at most 5
  repositories, emit a single CONFIRM per batch, and verify between
  batches.

## Remediation guidance

Each layer's fix is summarised below; the step sections above carry the
full probe commands and worked examples.

Per-layer fix table moved to
[references/error-handling.md](references/error-handling.md).

## Recent AWS features (2024-2026)
Recent AWS feature notes moved to
[references/advanced-patterns.md](references/advanced-patterns.md).


## References (load on demand)

- [references/advanced-patterns.md](references/advanced-patterns.md) — mindset, philosophy, Step 0 non-obvious behaviours, recent AWS features (moved from this file)
- [references/diagnostic-commands.md](references/diagnostic-commands.md) — account-wide pre-flight commands, repository-state short-circuit, and every step's probe, fix, and pattern-table commands (moved from this file)
- [references/worked-examples.md](references/worked-examples.md) — LIFECYCLE_DELETED worked example and the INSUFFICIENT_DATA re-prompt template (moved from this file)
- [references/error-handling.md](references/error-handling.md) — per-layer remediation fix table (moved from this file)
- [references/ecr-auth-and-policy-reference.md](references/ecr-auth-and-policy-reference.md) — auth token mechanics, repository vs IAM policy evaluation
- [references/ecr-lifecycle-replication-reference.md](references/ecr-lifecycle-replication-reference.md) — lifecycle policy evaluation and replication behaviour

## Domain

AWS CloudOps / Container Registry Operations, Image Distribution,
Identity & Access Management for ECR, KMS Encryption for Registries,
Cross-Region Replication, and Container Architecture Compatibility.

## AWS documentation

- **Amazon ECR User Guide** — https://docs.aws.amazon.com/AmazonECR/latest/userguide/what-is-ecr.html
- **ECR private registry settings** — https://docs.aws.amazon.com/AmazonECR/latest/userguide/registry.html
- **ECR repository policies** — https://docs.aws.amazon.com/AmazonECR/latest/userguide/repository-policies.html
- **ECR lifecycle policies** — https://docs.aws.amazon.com/AmazonECR/latest/userguide/lifecycle_policy_examples.html
- **ECR image tag immutability** — https://docs.aws.amazon.com/AmazonECR/latest/userguide/image-tag-mutability.html
- **ECR KMS encryption** — https://docs.aws.amazon.com/AmazonECR/latest/userguide/encryption-at-rest.html
- **ECR cross-region replication** — https://docs.aws.amazon.com/AmazonECR/latest/userguide/replication.html
- **ECR pull-through cache** — https://docs.aws.amazon.com/AmazonECR/latest/userguide/pull-through-cache.html
- **ECR image scanning** — https://docs.aws.amazon.com/AmazonECR/latest/userguide/image-scanning.html
- **ECR Public registry** — https://docs.aws.amazon.com/AmazonECR/latest/userguide/public-registries.html
