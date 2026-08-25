# ECR Replication Deployer — advanced patterns (moved from SKILL.md)

Loaded on demand — content moved verbatim from SKILL.md (progressive disclosure; nothing deleted).
## Mindset — three misconceptions (moved from SKILL.md)
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

## Configuration dependency graph (novel heuristic) (moved from SKILL.md)

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

## Expert heuristic: replicated images are read-only (moved from SKILL.md)

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

## Step 10 — Recent features (moved from SKILL.md)

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
