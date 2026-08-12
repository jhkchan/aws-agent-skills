---
name: ecr-replication-deployer
description: >-
  Provisions Amazon ECR cross-region and cross-account replication
  with production defaults: registry-level replication configuration
  (put-registry-replication-configuration), replication rules
  (source → destination region and registry), cross-account
  replication (destination registry ID), pull-through cache rules
  (upstream registry URL — ecr-public, quay.io, docker.io, k8s.io),
  cache pull permissions (Lambda/ECS pulls from cached image),
  replication lag awareness, cost per replicated image (storage in
  both regions), CloudWatch metrics for replication
  (ImageReplicationStatus), batch delete protection for replicated
  images, and deletion policy for source vs replica. Emits a
  READY_TO_DEPLOY checklist with verification commands. Use when
  configuring ECR cross-region replication, cross-account ECR
  replication, ECR pull-through cache, or multi-region container
  image availability. Triggers: configure ecr replication, ecr
  cross-region replication, ecr cross-account replication, ecr
  pull-through cache, ecr replication rule, ecr registry replication.
version: 0.1.0
author: Jacky Chan — AWS Community Builder
license: Apache-2.0
compatibility: >-
  Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf,
  Codex, Gemini). For live deployment: AWS CLI v2 with ecr access
  (and cross-account IAM if cross-account replication). Works with
  Terraform aws_ecr_replication_configuration /
  aws_ecr_pull_through_cache_rule resources and CloudFormation
  AWS::ECR::ReplicationConfiguration templates.
keywords:
  - aws
  - ecr
  - elastic container registry
  - replication
  - cross-region
  - cross-account
  - pull-through cache
  - cloudops
  - deploy
  - provisioning
  - container registry
  - docker
  - devtools
tags:
  - aws
  - ecr
  - replication
  - cloudops
  - deploy
  - devtools
  - provisioning
  - cross-region
  - cross-account
  - pull-through-cache
  - container-registry
dependencies:
  - aws-orchestrator
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: true
  phase: 1
  supports_pipeline: true
  entry_point: false
  family: DevTools
  task_type: deploy
  skill_class: capability
  lifecycle_status: active
  verdict_shape: "READY_TO_DEPLOY | PREREQUISITES_MISSING"
  version: 0.1.0
  author: "Jacky Chan — AWS Community Builder"
  tags:
    - aws
    - ecr
    - replication
    - cloudops
    - deploy
    - devtools
    - provisioning
    - cross-region
    - cross-account
    - pull-through-cache
    - container-registry
  dependencies:
    - aws-orchestrator
  keywords:
    - configure ecr replication
    - ecr cross-region replication
    - ecr cross-account replication
    - ecr pull-through cache
    - ecr replication rule
    - ecr registry replication
    - ecr pull-through cache rule
    - ecr replication configuration
  when_to_use: >-
    Invoke when the user wants to configure ECR cross-region
    replication, cross-account ECR replication, ECR pull-through
    cache rules (for docker.io, quay.io, k8s.io, ecr-public upstream
    registries), multi-region container image availability for DR,
    or understand replication lag and cost implications. Do NOT
    invoke for ECR repository lifecycle policies (separate skill),
    ECR image scanning, or ECS/EKS task deployment.
---

# ECR Replication Deployer

An AWS CloudOps agent skill that provisions Amazon ECR cross-region
and cross-account replication with correct defaults. The skill walks
the operator through registry-level replication configuration,
replication rules (source → destination), cross-account destination
registry IDs, pull-through cache rules for external registries
(docker.io, quay.io, k8s.io, ecr-public), replication lag awareness,
cost per replicated image (storage in both regions), CloudWatch
monitoring metrics (ImageReplicationStatus), batch delete protection
for replicated images, and deletion policy for source vs replica,
captures all configuration decisions, explains why each default
matters, and emits a READY_TO_DEPLOY checklist with copy-pasteable
verification commands.

## Activation keywords

configure ECR replication, ECR cross-region replication, ECR cross-
account replication, ECR pull-through cache, ECR replication rule,
ECR registry replication, ECR pull-through cache rule.

## STRICT output contract

When this skill is invoked with an ECR-replication-provisioning
request (configure cross-region replication, set up cross-account
replication, create a pull-through cache rule, or a partial
configuration), the agent MUST respond with the READY_TO_DEPLOY
checklist defined in the "Output format" section using the literal
all-caps labels `ECR_REPLICATION:`, `VERDICT:`, `CHECKLIST:`, and
`VERIFICATION_COMMANDS:`. Do NOT preface the checklist with prose,
headings, or disclaimers — emit the block as the first lines of the
response. This contract is what assertion-based evals and downstream
provisioning pipelines rely on; deviating from the literal labels
breaks automation silently.

If any prerequisite is missing, the verdict is `PREREQUISITES_MISSING`
with a specific gap citation in the checklist (marked `[✗]`), and
`READY_TO_DEPLOY` MUST NOT also appear.

## Quick navigation

| Section | When to read |
|---|---|
| Prerequisites | Always — verify before provisioning |
| Step 1 — Registry-level replication model | Core model |
| Step 2 — Cross-region replication | Same-account multi-region |
| Step 3 — Cross-account replication | Cross-account sharing |
| Step 4 — Pull-through cache rules | External registry caching |
| Step 5 — Replication lag and timing | Eventual consistency |
| Step 6 — Cost per replicated image | Storage cost awareness |
| Step 7 — CloudWatch metrics | Monitoring |
| Step 8 — Batch delete protection | Replica immutability |
| Step 9 — Deletion policy (source vs replica) | Cleanup |
| Step 10 — Recent features | Latest |
| NEVER do these things | Review before signing off |
| Output format | The literal checklist template |
| references/cross-region-and-cross-account.md | Replication detail |
| references/pull-through-cache-and-cost.md | Cache + cost detail |

## Mindset

**One-line takeaway:** ECR replication is configured at the REGISTRY
level — ALL repositories in the source registry replicate to the
destination. You cannot replicate individual repositories.
Replicated images are READ-ONLY in the destination (you cannot push
to a replica). Pull-through cache rules let you cache external images
(docker.io, quay.io, k8s.io, ecr-public) locally so that Lambda/ECS
pulls from the cached copy without hitting the external registry.

Three misconceptions dominate ECR replication misdesign at
provisioning time:

- **"I can replicate individual repositories."** You cannot. ECR
  replication is at the REGISTRY level. When you configure
  replication, ALL repositories in the source registry replicate to
  the destination. If you only need specific repositories, consider
  cross-account repository policies or pull-through cache instead of
  full registry replication.

- **"Replicated images are writable in the destination."** They are
  NOT. Replicated images are READ-ONLY in the destination registry.
  You can PULL from a replica but you cannot PUSH to it. If you need
  to push images to multiple regions, use a CI/CD pipeline to push to
  each regional ECR independently, not replication.

- **"Pull-through cache and replication are the same thing."** They
  are NOT. Replication copies images FROM your own ECR registry to
  another region/account's ECR registry (internal-to-internal).
  Pull-through cache fetches images FROM external registries
  (docker.io, quay.io, k8s.io, ecr-public) and caches them in your
  ECR (external-to-internal). Pull-through cache reduces external
  dependency latency and rate-limit issues.

## Configuration dependency graph (novel heuristic)

ECR replication configurations are NOT independent. Replication is at
the registry level. Cross-account requires the destination account's
registry ID. Pull-through cache requires upstream registry
connectivity. Use this graph to sequence provisioning.

| Configuration | Hard dependencies (API error without) | Silent failure / immutability | Enables downstream |
|---|---|---|---|
| Registry replication config (put-registry-replication-configuration) | Source registry exists; destination region identified | replication applies to ALL repos in the source registry; cannot select individual repos | images replicate to destination |
| Cross-account replication | Destination account registry ID known; destination account has NOT disabled replication | destination registry ID must be a 12-digit AWS account ID; if wrong, replication silently fails | images replicate cross-account |
| Pull-through cache rule | Upstream registry URL valid (ecr-public, quay.io, docker.io, k8s.io) | upstream registry must be reachable; if URL is wrong, pulls return error (not at config time) | local cached copy of external images |
| Replicated image pull | Replication completed (check ImageReplicationStatus) | if replication lag > expected, the image may not be in the destination yet — pulls will fail with ImageNotFound | Lambda/ECS pulls from regional replica |
| Batch delete on replica | Image is a replica (not source-pushed) | batch delete is BLOCKED on replicated images in the destination — they are read-only | deletion must happen at the source |
| CloudWatch monitoring | Replication configured | ImageReplicationStatus metric appears only after replication is configured | operational visibility |

**The registry-level-scope row is the one a baseline model misses.**
A baseline model may think replication can be configured per-repo.
It cannot — replication is at the registry level. Configuring
replication means ALL current and future repositories in the source
registry will replicate to the destination.

**Cross-dependency gotchas:**
- Replicated images are READ-ONLY. You cannot push, tag, or delete
  them in the destination. Deletion must happen at the source, which
  then propagates to the replica (if the source image is deleted, the
  replica is NOT automatically deleted — you must delete it manually
  in the destination).
- Pull-through cache rules require the upstream registry URL to match
  exactly one of the supported types: `ecr-public`, `quay.io`,
  `docker.io`, or `k8s.io`. Custom registry URLs are not supported.
- Cross-account replication requires the DESTINATION account to have
  not disabled replication. If the destination has the registry
  setting `REPLICATION_DISALLOWED`, replication silently fails.
- Replication lag is typically seconds to minutes, but for large
  images or cross-region, it can take longer. Always check
  `ImageReplicationStatus` before deploying from a replica.

## Expert heuristic: replication is registry-level

A baseline model may try to configure replication per-repo (like
Lifecycle Policies). The correct heuristic recognizes that ECR
replication is at the REGISTRY level.

```text
ECR replication scope:
  ├── Registry-level replication (ALL repos replicate)
  │     API: put-registry-replication-configuration
  │     Scope: every repository in the source registry
  │     Cannot select individual repos
  │
  ├── Cross-region (same account)
  │     Destination: same account, different region
  │     Use case: DR, low-latency multi-region pulls
  │
  ├── Cross-account (different account)
  │     Destination: different account (by registry ID)
  │     Use case: sharing images across accounts without per-repo policy
  │     Requirement: destination must allow replication
  │
  └── NOT replication (per-repo):
        ├── Cross-account repository policy → selective sharing
        └── Lifecycle policy → image cleanup/retention
```

**Key implication:** if you only need to share specific repositories
across accounts, use cross-account repository policies instead of
full registry replication. Replication is all-or-nothing per
registry.

## Expert heuristic: pull-through cache reduces external dependency

A baseline model may not distinguish pull-through cache from
replication. The correct heuristic recognizes that pull-through cache
fetches external images into your ECR for local caching.

```text
Pull-through cache vs replication:
  ├── Replication (internal → internal)
  │     Source: your ECR in region A
  │     Destination: your ECR in region B (or another account)
  │     Trigger: push to source → replicates automatically
  │     Images: your own images
  │
  └── Pull-through cache (external → internal)
        Source: docker.io, quay.io, k8s.io, ecr-public
        Destination: your ECR
        Trigger: Lambda/ECS pulls → fetches and caches on first pull
        Images: third-party images (nginx, redis, etc.)
```

**Key implication:** pull-through cache solves two problems:
1. **External rate limits** — docker.io has pull rate limits. Cached
   pulls bypass the external registry.
2. **Latency** — pulling from a local ECR is faster than pulling from
   docker.io across the internet.

## Expert heuristic: replicated images are read-only

A baseline model may assume that once an image is replicated, it can
be modified in the destination. The correct heuristic recognizes that
replicated images are READ-ONLY.

```text
Replicated image operations:
  Source registry (writable):
    ├── docker push → allowed
    ├── docker pull → allowed
    ├── docker tag → allowed
    └── batch delete → allowed (triggers replica orphaning)

  Destination registry (read-only replica):
    ├── docker push → DENIED (replica is read-only)
    ├── docker pull → allowed
    ├── docker tag → DENIED
    └── batch delete → DENIED (batch delete blocked on replicas)
```

**Key implication:** to delete a replicated image, you must delete it
at the SOURCE, then manually delete the orphaned replica in the
destination. Deleting the source does NOT auto-delete the replica.

## Prerequisites (verify before provisioning)

Before emitting provisioning commands, verify these prerequisites. If
any are missing, the verdict is **PREREQUISITES_MISSING**.

| Prerequisite | Why it matters | How to verify |
|---|---|---|
| Source ECR registry exists | Replication source must be an existing registry | `aws ecr describe-registry` |
| Source repositories have images | Replication copies existing and future images | `aws ecr describe-repositories` |
| Destination region identified (cross-region) | Replication target region | Confirm region name |
| Destination account ID (cross-account) | Cross-account replication needs 12-digit account ID | `aws sts get-caller-identity` (in destination) |
| Destination registry allows replication (cross-account) | Destination must not have REPLICATION_DISALLOWED | Verify destination registry settings |
| Upstream registry URL valid (pull-through cache) | Must be ecr-public, quay.io, docker.io, or k8s.io | Confirm upstream type |
| IAM permission for ecr:PutReplicationConfiguration | Configuring replication requires this permission | Verify IAM policy |
| Region settings support replication | Some restricted regions may not support ECR replication | Confirm region availability |

If any prerequisite is missing, output `VERDICT: PREREQUISITES_MISSING`
and cite the specific gap.

## Step 1 — Registry-level replication model

ECR replication is configured at the registry level using
`put-registry-replication-configuration`. This is a single API call
that defines all replication rules for the entire registry.

| Concept | Description |
|---|---|
| Source registry | The registry where images are pushed (primary) |
| Destination | The target region/account where images are replicated |
| Replication rule | A single source → destination mapping |
| Scope | ALL repositories in the source registry (no per-repo filtering) |
| Image state | Replicated images are READ-ONLY in the destination |

```bash
# Check current replication configuration
aws ecr describe-registry --region us-east-1
```

## Step 2 — Cross-region replication

Cross-region replication copies images from the source region to one
or more destination regions within the SAME account.

```bash
aws ecr put-registry-replication-configuration \
  --replication-configuration '{
    "rules": [
      {
        "destinations": [
          {
            "region": "us-west-2",
            "registryId": "111122223333"
          },
          {
            "region": "eu-west-1",
            "registryId": "111122223333"
          }
        ]
      }
    ]
  }' \
  --region us-east-1
```

**Key points:**
- `registryId` is the 12-digit AWS account ID (same for cross-region
  within the same account).
- Multiple destinations can be specified in a single rule.
- Once configured, ALL repositories in us-east-1 replicate to both
  us-west-2 and eu-west-1.

**Verify replication is working:**

```bash
# Push an image to the source
docker push 111122223333.dkr.ecr.us-east-1.amazonaws.com/my-app:latest

# Check replication status
aws ecr describe-images \
  --repository-name my-app \
  --image-ids imageTag=latest \
  --region us-west-2 \
  --query 'imageDetails[0].imageTags' \
  --registry-id 111122223333
```

## Step 3 — Cross-account replication

Cross-account replication copies images from the source account to a
destination account. The destination account ID is specified as the
`registryId`.

```bash
aws ecr put-registry-replication-configuration \
  --replication-configuration '{
    "rules": [
      {
        "destinations": [
          {
            "region": "us-east-1",
            "registryId": "999999999999"
          }
        ]
      }
    ]
  }' \
  --region us-east-1
```

**Critical:** the destination account (999999999999) must NOT have
replication disabled. By default, registries allow incoming
replication. If the destination has set the registry policy to
disallow replication, images will not replicate.

**Combined cross-region and cross-account:**

```bash
aws ecr put-registry-replication-configuration \
  --replication-configuration '{
    "rules": [
      {
        "destinations": [
          {"region": "us-east-1", "registryId": "999999999999"},
          {"region": "us-west-2", "registryId": "999999999999"}
        ]
      },
      {
        "destinations": [
          {"region": "eu-west-1", "registryId": "111122223333"}
        ]
      }
    ]
  }' \
  --region us-east-1
```

## Step 4 — Pull-through cache rules

Pull-through cache rules fetch and cache external images in your ECR.
When Lambda/ECS pulls an image matching a cache rule, ECR fetches it
from the upstream registry and caches it locally.

```bash
# Create a pull-through cache rule for docker.io
aws ecr create-pull-through-cache-rule \
  --ecr-repository-prefix docker-hub/ \
  --upstream-registry-url registry-1.docker.io \
  --region us-east-1

# Create a pull-through cache rule for quay.io
aws ecr create-pull-through-cache-rule \
  --ecr-repository-prefix quay/ \
  --upstream-registry-url quay.io \
  --region us-east-1

# Create a pull-through cache rule for k8s.io
aws ecr create-pull-through-cache-rule \
  --ecr-repository-prefix k8s/ \
  --upstream-registry-url registry.k8s.io \
  --region us-east-1

# Create a pull-through cache rule for ecr-public
aws ecr create-pull-through-cache-rule \
  --ecr-repository-prefix ecr-public/ \
  --upstream-registry-url public.ecr.aws \
  --region us-east-1
```

**Supported upstream registries:**

| Upstream | URL | ECR prefix example |
|---|---|---|
| Docker Hub | `registry-1.docker.io` | `docker-hub/` |
| Quay.io | `quay.io` | `quay/` |
| Kubernetes | `registry.k8s.io` | `k8s/` |
| ECR Public | `public.ecr.aws` | `ecr-public/` |

**Pulling a cached image:**

```bash
# Instead of: docker pull nginx:latest
# Use the pull-through cache prefix:
docker pull 111122223333.dkr.ecr.us-east-1.amazonaws.com/docker-hub/library/nginx:latest
```

**Key points:**
- The `ecr-repository-prefix` maps to a namespace in your ECR. All
  pulls via this prefix create repositories under that namespace.
- The first pull triggers the cache fetch (slower); subsequent pulls
  use the cached copy (faster).
- Pull-through cache repositories are managed by ECR — you cannot
  push to them manually.

## Step 5 — Replication lag and timing

Replication is asynchronous. After pushing an image to the source,
there is a lag before it appears in the destination.

```text
Replication lag expectations:
  ├── Same-region cross-account: seconds to ~1 minute
  ├── Cross-region (same continent): seconds to ~2 minutes
  ├── Cross-region (intercontinental): 1-5 minutes
  └── Large images (>1GB): add transfer time (proportional to size)
```

**Checking replication status:**

```bash
# Check image replication status via CloudWatch
aws cloudwatch get-metric-statistics \
  --namespace AWS/ECR \
  --metric-name ImageReplicationStatus \
  --dimensions Name=RepositoryName,Value=my-app \
  --start-time $(date -u -v-1H +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 \
  --statistics Sum \
  --region us-east-1
```

**Important:** always verify replication completed before deploying
from a replica. If the image has not replicated yet, pulls will fail
with `ImageNotFoundException`.

## Step 6 — Cost per replicated image

Replicated images incur storage costs in BOTH the source and
destination regions. This doubles the storage cost per image.

```text
Cost model:
  Source region: ECR storage cost per GB-month
  Destination region: ECR storage cost per GB-month (SAME rate)
  Total storage cost: 2x normal (source + each destination)

  Data transfer:
  ├── Source → Destination (replication): AWS data transfer rates
  └── Destination → Lambda/ECS (pull): standard ECR data transfer (free in-region)
```

**Key implication:** replication doubles (or triples for multi-
destination) storage costs. For cost optimization:
- Use lifecycle policies to prune old images in BOTH source and
  destinations.
- Replicate only to regions where you actually deploy.
- Consider pull-through cache instead of replication for third-party
  images (only one copy cached, not replicated across regions).

## Step 7 — CloudWatch metrics for replication

ECR provides CloudWatch metrics for monitoring replication status.

| Metric | Description |
|---|---|
| `ImageReplicationStatus` | Count of images by replication status (Complete, Failed, InProgress) |
| `RepositoryCount` | Number of repositories in the registry |
| `ImageCount` | Number of images across all repositories |
| `StorageUsed` | Total storage used in bytes |

```bash
# Create a CloudWatch alarm for replication failures
aws cloudwatch put-metric-alarm \
  --alarm-name "ECR-Replication-Failures" \
  --namespace AWS/ECR \
  --metric-name ImageReplicationStatus \
  --dimensions Name=RepositoryName,Value=my-app \
  --statistic Sum \
  --period 300 \
  --threshold 1 \
  --comparison-operator GreaterThanOrEqualToThreshold \
  --evaluation-periods 1 \
  --alarm-actions "arn:aws:sns:us-east-1:111122223333:ecr-alerts"
```

## Step 8 — Batch delete protection for replicated images

Replicated images CANNOT be batch-deleted in the destination
registry. They are read-only. This is a safety mechanism.

```bash
# This will FAIL on a replicated image in the destination:
aws ecr batch-delete-image \
  --repository-name my-app \
  --image-ids imageTag=latest \
  --region us-west-2
# Error: ImageNotFoundException or "replicated images cannot be deleted"
```

**To remove a replicated image:**
1. Delete the image at the SOURCE.
2. Manually delete the orphaned replica in the destination (it is
   now a regular image, not tied to a source image).

**Important:** deleting the source image does NOT automatically
delete the replica. You must clean up the destination manually or use
a lifecycle policy in the destination.

## Step 9 — Deletion policy (source vs replica)

| Action | Source registry | Destination registry (replica) |
|---|---|---|
| Push image | Allowed | Denied (read-only) |
| Delete image | Allowed (batch-delete-image) | Denied (batch-delete blocked on replicas) |
| Delete repository | Allowed | Allowed (but replicas reappear if source re-pushes) |
| Lifecycle policy | Runs independently | Runs independently (apply to both) |

**Recommended deletion workflow:**

```text
1. Delete image at source:
   aws ecr batch-delete-image --repository-name my-app --image-ids imageTag=v1.0 --region us-east-1

2. Delete orphaned replica in each destination:
   aws ecr batch-delete-image --repository-name my-app --image-ids imageTag=v1.0 --region us-west-2
   (This works AFTER the source image is deleted — the replica becomes a standalone image)

3. Apply lifecycle policies in BOTH source and destinations for automated cleanup.
```

## Step 10 — Recent features

**Recent AWS features (2023-2026):**

- **Pull-through cache GA (2022-2023):** ECR pull-through cache rules
  became generally available for docker.io, quay.io, and
  k8s.io upstream registries. This reduced external dependency
  latency and rate-limit issues for Lambda/ECS workloads.

- **Cross-account replication simplification (2023):** AWS
  streamlined the cross-account replication setup, requiring only
  the destination registry ID without additional per-repo policies
  for replicated images.

- **Terraform aws_ecr_replication_configuration (2023-2024):** The
  Terraform provider added the `aws_ecr_replication_configuration`
  and `aws_ecr_pull_through_cache_rule` resources for declarative
  management.

- **ECR pull-through cache for k8s.io (2024):** AWS added
  `registry.k8s.io` as a supported upstream registry for pull-through
  cache, enabling Kubernetes users to cache official images locally.

- **Replication performance improvements (2024-2025):** AWS improved
  replication throughput for large images, reducing cross-region lag
  for multi-gigabyte container images.

- **CloudWatch enhanced replication metrics (2025-2026):** AWS added
  more granular CloudWatch dimensions for ImageReplicationStatus,
  enabling per-region and per-registry monitoring dashboards.

## NEVER do these things

1. **NEVER assume replication is per-repository.** Replication is at
   the REGISTRY level. Configuring replication replicates ALL repos.
   Use cross-account repo policies for selective sharing.

2. **NEVER try to push to a replicated image in the destination.**
   Replicated images are READ-ONLY. Push to the source only.

3. **NEVER assume deleting the source image deletes the replica.**
   The replica becomes orphaned and must be deleted manually in the
   destination, or cleaned up via lifecycle policy.

4. **NEVER use batch-delete-image on a replicated image in the
   destination while it is still linked to the source.** It will
   fail. Delete the source image first, then the orphaned replica.

5. **NEVER configure pull-through cache with an unsupported upstream
   URL.** Only `registry-1.docker.io`, `quay.io`, `registry.k8s.io`,
   and `public.ecr.aws` are supported. Custom URLs are rejected.

6. **NEVER ignore replication lag before deploying from a replica.**
   Always check `ImageReplicationStatus` to confirm the image has
   replicated. Deploying from a non-replicated image fails with
   `ImageNotFoundException`.

7. **NEVER forget that replication doubles storage costs.** Each
   destination region incurs the same storage cost as the source.
   Apply lifecycle policies in BOTH source and destinations.

8. **NEVER configure cross-account replication without verifying the
   destination allows it.** If the destination has
   `REPLICATION_DISALLOWED`, replication silently fails.

9. **NEVER confuse pull-through cache with replication.** Pull-
   through cache fetches EXTERNAL images into your ECR. Replication
   copies YOUR images across regions/accounts.

10. **NEVER assume replication is instant for large images.**
    Replication lag for multi-GB images can be minutes. Always verify
    before deploying.

## Output format

```text
ECR_REPLICATION: <source-registry-id> (region: <source-region>) → <destinations>
VERDICT: READY_TO_DEPLOY | PREREQUISITES_MISSING
CHECKLIST:
  [✓|✗] Source registry: <registry-id> (region: <source-region>)
  [✓|✗] Replication type: Cross-region | Cross-account | Both | Pull-through cache
  [✓|✗] Destinations: <region:registry-id list>
  [✓|✗] Registry scope: ALL repositories (registry-level — no per-repo filtering)
  [✓|✗] Replicated images: READ-ONLY in destination
  [✓|✗] Pull-through cache rules: <prefix→upstream list> | none
  [✓|✗] Replication lag: expected <X> minutes (verified ImageReplicationStatus)
  [✓|✗] Storage cost: <source + destinations> regions (doubles/triples storage)
  [✓|✗] Batch delete: BLOCKED on replicas (delete at source first)
  [✓|✗] Lifecycle policies: applied in source AND destinations | WARNING (missing in destination)
  [✓|✗] CloudWatch monitoring: ImageReplicationStatus alarm configured | not configured
  [✓|✗] Tags: <key=value list>
VERIFICATION_COMMANDS:
  aws ecr describe-registry --region <source-region>
  aws ecr describe-repositories --region <destination-region>
  aws cloudwatch get-metric-statistics --namespace AWS/ECR --metric-name ImageReplicationStatus
```

### Worked example — cross-region replication with pull-through cache

```text
ECR_REPLICATION: 111122223333 (region: us-east-1) → us-west-2:111122223333, eu-west-1:111122223333
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓] Source registry: 111122223333 (region: us-east-1)
  [✓] Replication type: Cross-region (same account)
  [✓] Destinations: us-west-2:111122223333, eu-west-1:111122223333
  [✓] Registry scope: ALL repositories (registry-level)
  [✓] Replicated images: READ-ONLY in destination
  [✓] Pull-through cache rules: docker-hub/ → registry-1.docker.io, quay/ → quay.io
  [✓] Replication lag: expected 1-2 minutes (verified ImageReplicationStatus)
  [✓] Storage cost: 3 regions (source + 2 destinations = 3x storage)
  [✓] Batch delete: BLOCKED on replicas (delete at source first)
  [✓] Lifecycle policies: applied in source AND destinations
  [✓] CloudWatch monitoring: ImageReplicationStatus alarm configured
  [✓] Tags: Environment=production, Pattern=multi-region
VERIFICATION_COMMANDS:
  aws ecr describe-registry --region us-east-1
  aws ecr describe-repositories --region us-west-2
  aws cloudwatch get-metric-statistics --namespace AWS/ECR --metric-name ImageReplicationStatus
```

## Error handling

### Replication not working (images not appearing in destination)
- Verify the destination registry ID is correct (12-digit account ID).
- For cross-account, verify the destination has not disabled
  replication (check registry settings).
- Check CloudWatch `ImageReplicationStatus` for `FAILED` status.

### Pull-through cache pull fails
- Verify the upstream registry URL is one of the supported types.
- Verify the ECR repository prefix matches the cache rule.
- Check network connectivity to the upstream registry.

### Batch delete fails on a replicated image
- Replicated images are read-only. Delete the image at the source
  first, then delete the orphaned replica in the destination.

### Storage costs higher than expected
- Each destination region adds storage cost. Apply lifecycle policies
  in BOTH source and destinations to prune old images.
- Check for orphaned replicas (source image deleted but replica
  remains). These still incur storage cost.

## Domain

AWS CloudOps / Amazon ECR Cross-Region and Cross-Account Replication
& Pull-Through Cache Provisioning.

## AWS documentation

- **ECR replication** — https://docs.aws.amazon.com/AmazonECR/latest/userguide/replication.html
- **Cross-region replication** — https://docs.aws.amazon.com/AmazonECR/latest/userguide/replication-cross-region.html
- **Cross-account replication** — https://docs.aws.amazon.com/AmazonECR/latest/userguide/replication-cross-account.html
- **Pull-through cache** — https://docs.aws.amazon.com/AmazonECR/latest/userguide/pull-through-cache.html
- **Pull-through cache rules** — https://docs.aws.amazon.com/AmazonECR/latest/userguide/create-pull-through-cache-rule.html
- **Registry replication API** — https://docs.aws.amazon.com/AmazonECR/latest/APIReference/API_PutRegistryReplicationConfiguration.html
- **CloudWatch ECR metrics** — https://docs.aws.amazon.com/AmazonECR/latest/userguide/cloudwatch-metrics.html
- **ECR lifecycle policies** — https://docs.aws.amazon.com/AmazonECR/latest/userguide/lifecycle_policy_definitions.html
