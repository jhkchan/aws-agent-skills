---
name: ecr-push-pull-troubleshooter
description: 'Diagnoses Amazon ECR push and pull failures through a fourteen-category diagnostic tree: authentication (docker login token expiry, IAM ecr:GetAuthorizationToken), repository policy vs IAM policy precedence, lifecycle policy prematurely deleting images, image size limit (10 GB), cross-region replication lag, KMS encryption key access denied, registry alias confusion (public vs private), scan-on-push findings blocking deployment, image tag immutability conflicts, docker manifest errors, pull-through cache misconfiguration, Fargate/ECS platform version vs image architecture mismatch (arm64 vs x86_64), layer download failures, and throttling. Walks symptoms to a verified root cause with evidence-backed probes; emits ROOT_CAUSE_IDENTIFIED or INSUFFICIENT_DATA.'
version: 0.1.0
author: Jacky Chan — AWS Community Builder
license: Apache-2.0
compatibility: Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). Offline symptom classification works from pasted docker / aws ecr error output. Live-account diagnosis uses aws ecr
keywords:
- ECR
- docker login
- authorization token
- ecr:GetAuthorizationToken
- repository policy
- lifecycle policy
- tag immutability
- image size limit
- cross-region replication
- KMS encryption
- registry alias
- public registry
- scan on push
- manifest
- pull-through cache
- Fargate architecture
- arm64
- x86_64
- layer download
- troubleshoot
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

A failing ECR push or pull is almost always an identity, policy, or
lifecycle incident, not a docker problem. Docker is the messenger —
the error string it surfaces is almost always the AWS-side denial
translated into docker terms. Senior container engineers do not start
by rebuilding the image; they start with `aws ecr get-authorization-token`,
the repository policy, and the lifecycle policy, and only rebuild once
auth, policy, and lifecycle are proven correct.

## Philosophy

Four behaviours separate a senior ECR engineer from a generalist:

- **The auth token is base64(username:password) and valid for 12 hours.**
  The decoded token's username is the literal string `AWS` and the
  password is a signed STS-style URL query string. After 12 hours the
  signature expires and every push/pull fails with `Your authorization
  token has expired`. CI pipelines that cache the token in
  `~/.docker/config.json` longer than 12 hours hit this deterministically
  once a day. The fix is to refresh the token before every build, not
  to extend the token.
- **Cross-account access requires BOTH sides.** The caller's
  identity-based policy must allow `ecr:BatchGetImage` and friends on
  the target repository ARN, AND the target repository's resource-based
  policy must list the caller's account (`aws:PrincipalAccount`) or ARN.
  Operators who "added the IAM permission to the CI role" but still see
  `denied` from a cross-account pull always missed the repository
  policy side.
- **Lifecycle policy is first-match-wins, evaluated top to bottom.** A
  broad `expire` rule placed above a narrower `keep` rule deletes what
  the `keep` rule would have protected. Operators who "set a 10-image
  retention rule" and lost images they needed almost always had an
  earlier rule match first.
- **The registry alias, the account ID, and the region are three
  different things.** `public.ecr.aws/<alias>/repo` is ECR Public;
  `<account>.dkr.ecr.<region>.amazonaws.com/repo` is ECR Private.
  `docker push public.ecr.aws/...` when the target was a private URI
  silently pushes to a different registry and the next pull fails with
  `manifest unknown`.

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

```bash
# 1. Registry settings (encryption, public alias, replication source)
aws ecr describe-registry --output json

# 2. Auth token (decode base64 to read username:password; valid for 12h)
aws ecr get-authorization-token --output json | \
  jq '.authorizationData[0] | {proxyEndpoint, expiresAt, token: (.authorizationToken | @base64d)}'

# 3. Repository configuration (imageTagMutability, scan-on-push, encryption)
aws ecr describe-repositories --repository-names <repo> --output json

# 4. Repository resource-based policy (cross-account grants live here)
aws ecr get-repository-policy --repository-name <repo> --output json 2>/dev/null || \
  echo "No repository policy (default deny for cross-account)"

# 5. Lifecycle policy (rule order matters — first match wins)
aws ecr get-lifecycle-policy --repository-name <repo> --output json 2>/dev/null || \
  echo "No lifecycle policy"

# 6. AWS Health (regional ECR events)
aws health describe-events --filter eventStatusCodes=OPEN,UPCOMING \
  --region us-east-1 --output json
```

### Repository-state short-circuit

| `describe-repositories` field | Effect on diagnosis |
|---|---|
| `imageTagMutability: IMMUTABLE` | A push with an existing tag fails with `image tag already exists` — route to TAG_IMMUTABILITY before any policy work. |
| `imageScanningConfiguration.scanOnPush: true` | Every push triggers a scan; downstream gates may block deploy on `HIGH`/`CRITICAL`. Route to SCAN_BLOCKING when the error is from the deploy pipeline. |
| `encryptionConfiguration.encryptionType: KMS` | Pushes need `kms:GenerateDataAccess`; pulls need `kms:Decrypt`. Route to KMS on any KMS.AccessDeniedException. |
| `encryptionConfiguration.encryptionType: AES256` | No caller-side KMS permission needed — do NOT chase KMS for AES256 repos. |
| Empty repository policy | Cross-account pulls fail with `denied`; same-account pulls succeed via IAM. Route to POLICY_REPOSITORY for cross-account. |

If the input is malformed (missing registry URI or repository name, no
symptom description, no caller context for cross-account diagnosis),
emit:

```text
TARGET: <registry-uri/repo:tag or unknown>
VERDICT: INSUFFICIENT_DATA
REASON: Input is missing required context — at minimum a symptom
  description (the docker / aws ecr error string) and the full
  registry URI (account, region, repository name).
LAYER: UNKNOWN
EVIDENCE:
  - Missing: <list specific missing fields>
REMEDIATION: Re-prompt the operator for: (1) the exact docker or aws
  ecr error string, (2) the full registry URI being pushed to or
  pulled from, and (3) for cross-account cases, the IAM principal
  doing the operation and its account ID.
```

## Process — Diagnostic decision tree (apply in symptom order)

The tree is symptom-driven. Pick the entry point based on the observed
symptom, then walk the layer-specific probes in order. **Never emit
ROOT_CAUSE_IDENTIFIED without a failing probe that matches the symptom.**

### Step 0: Non-obvious behaviours that change diagnosis

- **The auth token is the same password for all repositories in the
  registry.** `aws ecr get-login-password` returns one password scoped
  to the registry (`<account>.dkr.ecr.<region>.amazonaws.com`). Logging
  in once authorises push/pull to every repository in that registry —
  there is no per-repository login. A different region OR a different
  account is a different registry and needs a separate login.
- **The token in `~/.docker/config.json` is cached indefinitely by
  default.** Docker does not refresh the token; the cached entry stays
  until the next `docker login` overwrites it. A CI runner that caches
  `~/.docker/config.json` between jobs hits `Your authorization token
  has expired` deterministically once the 12-hour window elapses.
- **Repository policy and IAM policy combine with explicit-deny-wins.**
  An explicit `Deny` in either the IAM policy, the repository policy,
  or an SCP overrides any `Allow`. Implicit deny (no matching
  statement) in either policy also fails. For same-account access, IAM
  alone is sufficient; for cross-account, the repository policy must
  ALSO allow.
- **Lifecycle policy evaluation is first-match-wins, top to bottom.**
  Once a rule matches, its action (`expire`) is taken and no further
  rule is evaluated for that image. A broad `expire` rule placed above
  a narrower `keep` rule deletes images the `keep` rule would have
  protected. Always read rule order.
- **Tag immutability blocks overwrites, not first-push.** A new tag
  always succeeds; an existing tag always fails when `IMMUTABLE`.
  Switching mutability is per-repository and takes effect immediately.
- **Cross-region replication is asynchronous and eventually consistent.**
  After a push to the source region, the replica may take seconds to
  minutes to appear. A pull in the destination region before
  replication completes fails with `manifest unknown`. Replication
  rules do NOT replicate across accounts unless the destination is in
  the rule.
- **Scan-on-push findings do not block the push; they block the
  deploy.** ECR accepts the image, then runs the scan asynchronously.
  The push succeeds; a downstream CD gate reads
  `describe-image-scan-findings` and refuses to promote. Operators who
  say "the push was blocked by a CVE" almost always had a downstream
  gate do the blocking.
- **`describe-images` may briefly show a deleted image.** After a
  lifecycle `expire`, the image is marked for deletion and may still
  appear for up to 24 hours, then vanishes. CloudTrail `BatchDeleteImage`
  events from the ECR service principal are the actual delete record.
- **Image architecture is a property of the manifest, not the tag.**
  A tag like `app:v1` can point to a single-arch image (`linux/amd64`)
  or a multi-arch manifest list. A Fargate task on `x86_64` pulling a
  tag that resolves to a single-arch `arm64` image fails with `no
  matching manifest for platform linux/amd64 in the manifest list` (if
  multi-arch) or `failed to register layer: ...` (if single-arch arm64
  forced onto x86).

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

```bash
# Verify the token's expiry (the token is base64(AWS:<signed-url>))
aws ecr get-authorization-token --output json | \
  jq '.authorizationData[0] | {proxyEndpoint, expiresAt, decoded: (.authorizationToken | @base64d)}'

# Check what docker has cached
cat ~/.docker/config.json | jq '.auths'
```

The decoded token's password contains an `X-amz-expires=43200` (12-hour)
query parameter. If `expiresAt` is in the past, the cached credentials
are stale. If the token has expired, **ROOT_CAUSE_IDENTIFIED** with
`LAYER: AUTH_TOKEN_EXPIRED`. Fix: refresh the token immediately before
every push; do not cache credentials across jobs.

### Step 3: AUTH_IAM_DENIED — missing ecr:GetAuthorizationToken

Symptom: `denied: ... is not authorized to perform:
ecr:GetAuthorizationToken`. Without this permission, the caller cannot
retrieve an auth token at all.

```bash
aws iam simulate-principal-policy \
  --policy-source-arn <caller-arn> \
  --action-names ecr:GetAuthorizationToken \
  --output json --profile <p>
```

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

```bash
aws iam simulate-principal-policy \
  --policy-source-arn <caller-arn> \
  --action-names ecr:BatchCheckLayerAvailability ecr:BatchGetImage \
                ecr:GetDownloadUrlForLayer ecr:PutImage \
                ecr:InitiateLayerUpload ecr:UploadLayerPart \
                ecr:CompleteLayerUpload \
  --resource-arns arn:aws:ecr:<region>:<account>:repository/<repo> \
  --output json --profile <p>
```

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

```bash
aws ecr get-repository-policy --repository-name <repo> \
  --region <region> --output json --profile <p>
```

Same-account callers do NOT need a repository policy — IAM alone is
sufficient. Cross-account callers need BOTH the caller's IAM policy
AND a repository policy statement listing the caller's account or ARN.
If the policy is empty or does not list the caller's
`aws:PrincipalAccount`, **ROOT_CAUSE_IDENTIFIED** with
`LAYER: POLICY_REPOSITORY`. Fix:

```bash
aws ecr set-repository-policy --repository-name <repo> --region <region> \
  --policy-text '{
    "Version": "2012-10-17",
    "Statement": [{
      "Sid": "CrossAccountPull",
      "Effect": "Allow",
      "Principal": {"AWS": "arn:aws:iam::<caller-account>:root"},
      "Action": ["ecr:BatchGetImage", "ecr:GetDownloadUrlForLayer",
                 "ecr:BatchCheckLayerAvailability"]
    }]
  }' --profile <p>
```

Always confirm before changing a resource-based policy — a too-broad
principal can leak the repository.

### Step 6: LIFECYCLE_DELETED — lifecycle policy deleted the image

Symptom: image tag was present yesterday; today `manifest unknown` and
gone from `describe-images`. The operator did not delete it manually.

```bash
aws ecr get-lifecycle-policy --repository-name <repo> --output json --profile <p>
aws ecr describe-images --repository-name <repo> --output json --profile <p> | \
  jq '.imageDetails[] | {imageTags, imagePushedAt, imageSizeInBytes}'

# CloudTrail shows the ECR service principal deleting images
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=EventName,AttributeValue=BatchDeleteImage \
  --start-time $(date -d '-24 hours' +%s) --end-time $(date +%s) \
  --output json | jq '.Events[] | select(.CloudTrailEvent | contains("<repo>"))'
```

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

```bash
aws ecr describe-registry --output json --profile <p>
aws ecr get-replication-configuration --region <source-region> --output json --profile <p>
aws ecr describe-images --repository-name <repo> --region <dest-region> --output json --profile <p>
```

Replication rules are per-source-registry. If no rule covers the
repository's region and destination, no replication occurs. If a rule
exists, replication is asynchronous — typically seconds to minutes. If
no rule covers the destination, **ROOT_CAUSE_IDENTIFIED** with
`LAYER: REPLICATION_LAG`. If the rule exists but the image is missing
minutes after push, check AWS Health for replication service degradation.

### Step 9: KMS_ACCESS_DENIED — KMS encryption key access denied

Symptom: `KMS.AccessDeniedException` on push or pull when the
repository uses `encryptionType: KMS`.

```bash
aws ecr describe-repositories --repository-names <repo> --output json | \
  jq '.repositories[0].encryptionConfiguration'
aws kms describe-key --key-id <kms-key-id> --output json | \
  jq '.KeyMetadata.{KeyState, KeyManager, Origin}'
aws iam simulate-principal-policy \
  --policy-source-arn <caller-arn> \
  --action-names kms:GenerateDataAccess kms:Decrypt \
  --resource-arns arn:aws:kms:<region>:<account>:key/<key-id> \
  --output json --profile <p>
```

The pusher needs `kms:GenerateDataAccess`; the puller needs
`kms:Decrypt`. The key policy must also grant the ECR service principal
access (typically `kms:CreateGrant` to `ecr.<region>.amazonaws.com`).
If the simulation returns `implicitDeny`, **ROOT_CAUSE_IDENTIFIED**
with `LAYER: KMS_ACCESS_DENIED`. Fix: add the KMS permissions to the
caller's IAM policy AND verify the key policy grants ECR access.

### Step 10: REGISTRY_ALIAS_MISMATCH — public vs private registry confusion

Symptom: `manifest unknown` from some callers but not others; push
appears to succeed but the image is in a different registry.

```bash
# Identify which registry the URI points at:
# - public.ecr.aws/<alias>/<repo>             -> ECR Public
# - <account>.dkr.ecr.<region>.amazonaws.com  -> ECR Private
aws ecr-public describe-registries --output json --profile <p> | \
  jq '.registries[] | {registryId, aliases: [.aliases[] | .name]}'
```

If the URI host is `public.ecr.aws` but the operator intended a
private registry (or vice-versa), or the public alias is owned by a
different account, **ROOT_CAUSE_IDENTIFIED** with
`LAYER: REGISTRY_ALIAS_MISMATCH`. Fix: use the correct full URI and
authenticate to the correct registry.

### Step 11: SCAN_BLOCKING — scan findings block deploy

Symptom: docker push succeeds; the deploy pipeline refuses to promote
the image. The gate reads `describe-image-scan-findings` and blocks on
`HIGH` / `CRITICAL`.

```bash
aws ecr describe-image-scan-findings \
  --repository-name <repo> --image-id imageTag=<tag> \
  --output json --profile <p> | \
  jq '.imageScanFindings.findings[] | select(.severity == "HIGH" or .severity == "CRITICAL")'
```

ECR does NOT block pushes based on scan findings — a downstream gate
(CodeDeploy, a Lambda promotion step, a custom security gate) does the
blocking. If scan findings are the blocker, **ROOT_CAUSE_IDENTIFIED**
with `LAYER: SCAN_BLOCKING`. Surface the findings; do NOT recommend
bypassing without a security owner.

### Step 12: TAG_IMMUTABILITY — image tag overwrite rejected

Symptom: push fails with `image tag already exists and is immutable`.

```bash
aws ecr describe-repositories --repository-names <repo> --output json | \
  jq '.repositories[0].imageTagMutability'
```

`IMMUTABLE` blocks overwrites on the named repository only —
immutability is per-repository, not per-registry. Fix: use a new tag
(recommended for traceability) or switch to MUTABLE:

```bash
aws ecr put-image-tag-mutability --repository-name <repo> \
  --image-tag-mutability MUTABLE --profile <p>
```

If the repository is `IMMUTABLE` and the push is an overwrite,
**ROOT_CAUSE_IDENTIFIED** with `LAYER: TAG_IMMUTABILITY`.

### Step 13: MANIFEST_INVALID / ARCHITECTURE_MISMATCH — manifest and architecture issues

Symptom: `manifest unknown`, `no matching manifest for platform
linux/arm64 in the manifest list`, Fargate task stops with
`CannotPullContainerError`.

```bash
# Inspect the manifest (multi-arch manifests return a list)
docker manifest inspect <registry-uri>/<repo>:<tag> 2>/dev/null || \
  aws ecr batch-get-image --repository-name <repo> \
    --image-ids imageTag=<tag> --output json --profile <p> | \
  jq '.images[0].imageManifest' | head -50

# Fargate platform / Lambda architecture determine host platform
aws ecs describe-tasks --cluster <cluster> --tasks <task-id> --output json | \
  jq '.tasks[0] | {platformVersion}'
aws lambda get-function-configuration --function-name <name> --output json | \
  jq '.Architectures'
```

| Pattern | Cause |
|---|---|
| `no matching manifest for platform linux/amd64 in the manifest list` | The tag points to a single-arch arm64 image; the host is x86_64 (or vice-versa). Build a multi-arch manifest with `docker buildx`. |
| Fargate task fails after pull with `Exec format error` | Image is single-arch and was force-pulled onto an incompatible host (rare — Fargate matches on manifest). |
| Lambda `ImagePullException: Image architecture arm64 incompatible` | Lambda with `Architectures: [x86_64]` cannot run an arm64-only image. Set `Architectures: [arm64]` OR rebuild for x86_64. |

If the manifest list does not include the requested platform or the
image is single-arch on the wrong host, **ROOT_CAUSE_IDENTIFIED** with
`LAYER: ARCHITECTURE_MISMATCH` (preferred) or `LAYER: MANIFEST_INVALID`
when the manifest is malformed.

### Step 14: PULL_THROUGH_CACHE — pull-through cache misconfiguration

Symptom: pull from a pull-through cache repository loops indefinitely;
upstream registry unreachable; pull fails with `upstream repository
does not exist`.

```bash
aws ecr describe-pull-through-cache-rules --region <region> --output json --profile <p>
```

| Pattern | Cause |
|---|---|
| `upstream registry does not exist` | Upstream URI is wrong, or upstream is unreachable from the region (network/egress). |
| Pull loops / never caches | Local cached repository name does not match the rule's prefix; `ecrRepositoryPrefix` misconfigured. |
| `KMS.AccessDeniedException` on pull-through | Cache writes to a KMS-encrypted repo; caller lacks `kms:Decrypt` on the local key. |
| Pull from a credentialled upstream fails | Upstream secret (Secrets Manager) is missing or stale; rule cannot authenticate to the upstream. |

If the rule is misconfigured or the upstream is unreachable,
**ROOT_CAUSE_IDENTIFIED** with `LAYER: PULL_THROUGH_CACHE`.

### Step 15: LAYER_DOWNLOAD_FAILED — layer download failures

Symptom: `failed to register layer: layer does not exist`,
`download failed after attempt=5`, retryable errors during `docker
pull` for specific layers.

```bash
aws ecr batch-check-layer-availability \
  --repository-name <repo> \
  --layer-digests sha256:<digest-1> sha256:<digest-2> \
  --output json --profile <p>
```

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

```text
TARGET: 111111111111.dkr.ecr.us-east-1.amazonaws.com/payments:v3
VERDICT: ROOT_CAUSE_IDENTIFIED
REASON: A lifecycle policy rule "expire when count=3, tagStatus=any"
  evaluated in first-match order and deleted the 4th-newest image,
  which happened to be the production release from 2 days ago.
LAYER: LIFECYCLE_DELETED
EVIDENCE:
  - Symptom: docker pull returns "manifest unknown" for payments:v3
    since 03:17 UTC; describe-images no longer lists v3.
  - Probe: get-lifecycle-policy top rule is {type: expire, selection:
    {count: 3, tagStatus: any}}.
  - Probe: cloudtrail lookup-events for BatchDeleteImage at 03:17 UTC
    shows the ECR service principal deleted digest sha256:abc123.
  - Passing: repository policy empty; no manual-delete CloudTrail event.
REMEDIATION:
  1. Re-push the image OR restore from a backup region's replica.
  2. Reorder the lifecycle policy so "keep last 10 tagged" rules sit
     ABOVE "expire count=3" rules; first matching rule wins.
  3. Add tag-rule protection for the prod-* tag prefix.
```

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

## Recent AWS features (2024-2026)

- **Pull-through cache for ECR Private (2024-2025):** Rules cache images from upstream registries (Docker Hub, Quay, ECR Public) on first pull. Common misconfigurations: prefix mismatches and upstream secret expiry.
- **ECR scan engine integration with Inspector (2024-2025):** Enhanced scan delegates to Amazon Inspector for deeper CVE coverage. Downstream gates may consume either source.
- **Lifecycle policy preview (2024-2025):** `start-lifecycle-policy-preview` dry-runs a policy and returns the would-be deletions. Always preview before applying a new policy.
- **Registry alias for ECR Public (2024):** Custom aliases; collisions produce REGISTRY_ALIAS_MISMATCH-class errors. Verify alias ownership via `ecr-public describe-registries`.
- **Fargate arm64 (Graviton) GA (2024):** Fargate supports `runtimePlatform: ARM64` on platform version 1.4.0+. A mismatch between task platform and image architecture fails the pull.

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
