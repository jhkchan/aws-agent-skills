---
name: ecr-replication-deployer
description: 'Provisions Amazon ECR cross-region and cross-account replication with production defaults: registry-level replication configuration (put-registry-replication-configuration), replication rules (source → destination region and registry), cross-account replication (destination registry ID), pull-through cache rules (upstream registry URL — ecr-public, quay.io, docker.io, k8s.io), cache pull permissions (Lambda/ECS pulls from cached image), replication lag awareness, cost per replicated image (storage in both regions), CloudWatch metrics for replication (ImageReplicationStatus), batch delete protection for replicated images, and deletion policy for source vs replica. Emits a READY_TO_DEPLOY checklist with verification commands. Use when configuring ECR cross-region replication, cross-account ECR replication, ECR pull-through cache, or. Triggers: configure ecr replication, ecr cross-region replication, ecr cross-account replication, ecr pull-through cache, ecr replication rule, ecr registry replication.'
license: Apache-2.0
compatibility: 'Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). For live deployment: AWS CLI v2 with ecr access (and cross-account IAM if cross-account replication). Works with Terraform aws_ecr_replication_configuration / aws_ecr_pull_through_cache_rule resources and CloudFormation AWS::ECR::ReplicationConfiguration templates.'
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: 'true'
  phase: '1'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: DevTools
  task_type: deploy
  skill_class: capability
  lifecycle_status: active
  verdict_shape: READY_TO_DEPLOY | PREREQUISITES_MISSING
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  tags: aws, ecr, replication, cloudops, deploy, devtools, provisioning, cross-region, cross-account, pull-through-cache, container-registry
  dependencies: aws-orchestrator
  keywords: aws, ecr, elastic container registry, replication, cross-region, cross-account, pull-through cache, cloudops, deploy, provisioning, container registry, docker, devtools
  when_to_use: Invoke when the user wants to configure ECR cross-region replication, cross-account ECR replication, ECR pull-through cache rules (for docker.io, quay.io, k8s.io, ecr-public upstream registries), multi-region container image availability for DR, or understand replication lag and cost implications. Do NOT invoke for ECR repository lifecycle policies (separate skill), ECR image scanning, or ECS/EKS task deployment.
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

The three provisioning misconceptions moved to
[references/advanced-patterns.md](references/advanced-patterns.md).

## Configuration dependency graph (novel heuristic)
Full dependency table and cross-dependency gotchas moved to
[references/advanced-patterns.md](references/advanced-patterns.md).

## Expert heuristic: replication is registry-level
Registry-level scope tree and key implication moved to
[references/cross-region-and-cross-account.md](references/cross-region-and-cross-account.md).

## Expert heuristic: pull-through cache reduces external dependency
Pull-through-cache vs replication tree and key implications moved to
[references/pull-through-cache-and-cost.md](references/pull-through-cache-and-cost.md).

## Expert heuristic: replicated images are read-only
Replica read-only operations tree and key implication moved to
[references/advanced-patterns.md](references/advanced-patterns.md).

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

Verify commands (push to source, check replica describe-images): [references/diagnostic-commands.md](references/diagnostic-commands.md).

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

Combined cross-region + cross-account configuration example moved to [references/cross-region-and-cross-account.md](references/cross-region-and-cross-account.md).

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

CloudWatch ImageReplicationStatus check command moved to [references/diagnostic-commands.md](references/diagnostic-commands.md).

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

CloudWatch alarm creation command for replication failures moved to [references/diagnostic-commands.md](references/diagnostic-commands.md).

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
Recent AWS feature notes (2023-2026) moved to
[references/advanced-patterns.md](references/advanced-patterns.md).

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
Failure modes and their fixes moved to
[references/error-handling.md](references/error-handling.md).

## References (load on demand)

- [references/advanced-patterns.md](references/advanced-patterns.md) — mindset misconceptions, configuration dependency graph, read-only replica heuristic, recent AWS features (moved from this file)
- [references/cross-region-and-cross-account.md](references/cross-region-and-cross-account.md) — cross-region/cross-account replication detail, registry-level scope heuristic, combined configuration example (heuristic and example moved from this file)
- [references/pull-through-cache-and-cost.md](references/pull-through-cache-and-cost.md) — pull-through cache and cost detail, pull-through-vs-replication heuristic (moved from this file)
- [references/diagnostic-commands.md](references/diagnostic-commands.md) — replication verify/status/alarm commands (moved from this file)
- [references/error-handling.md](references/error-handling.md) — replication not working, pull-through pull fails, batch delete on replica, storage cost (moved from this file)

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
