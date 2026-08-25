# Pull-Through Cache and Cost Management — ECR Replication Deployer

Deep reference on ECR pull-through cache rules (upstream registry
URLs, ECR prefix mapping, first-pull behavior, cache repository
management), replication cost model (storage doubling/tripling, data
transfer, lifecycle policy optimization), CloudWatch metrics for
monitoring replication status, and batch delete protection.
Loaded on demand by the skill — kept out of the main SKILL.md body
so the provisioning procedure stays scannable.

## Pull-through cache rules

### Supported upstream registries

| Upstream registry | URL | Common images |
|---|---|---|
| Docker Hub | `registry-1.docker.io` | nginx, redis, postgres, node |
| Quay.io | `quay.io` | CoreOS, Prometheus, operators |
| Kubernetes | `registry.k8s.io` | kube-apiserver, kube-proxy, coredns |
| ECR Public | `public.ecr.aws` | AWS-published images (amazonlinux, eks-distro) |

**Important:** the URL must match exactly. For Docker Hub, use
`registry-1.docker.io` (NOT `docker.io` or `hub.docker.com`).

### Creating pull-through cache rules

```bash
# Docker Hub
aws ecr create-pull-through-cache-rule \
  --ecr-repository-prefix docker-hub/ \
  --upstream-registry-url registry-1.docker.io \
  --region us-east-1

# Quay.io
aws ecr create-pull-through-cache-rule \
  --ecr-repository-prefix quay/ \
  --upstream-registry-url quay.io \
  --region us-east-1

# Kubernetes
aws ecr create-pull-through-cache-rule \
  --ecr-repository-prefix k8s/ \
  --upstream-registry-url registry.k8s.io \
  --region us-east-1

# ECR Public
aws ecr create-pull-through-cache-rule \
  --ecr-repository-prefix ecr-public/ \
  --upstream-registry-url public.ecr.aws \
  --region us-east-1
```

### Listing and verifying cache rules

```bash
# List all pull-through cache rules
aws ecr describe-pull-through-cache-rules --region us-east-1

# Verify a specific rule
aws ecr describe-pull-through-cache-rules \
  --ecr-repository-prefix docker-hub/ \
  --region us-east-1
```

### How pull-through cache works

```text
First pull (cache miss):
  Lambda/ECS → ECR (docker-hub/library/nginx:latest)
    ECR fetches from registry-1.docker.io/library/nginx:latest
    ECR stores the image layers locally (cached)
    ECR returns the image to Lambda/ECS
    → Slower (fetches from external registry)

Subsequent pulls (cache hit):
  Lambda/ECS → ECR (docker-hub/library/nginx:latest)
    ECR serves from local cache (no external fetch)
    → Faster (in-region, no rate limits)
```

### Pulling a cached image

```bash
# Instead of pulling directly from Docker Hub:
#   docker pull nginx:latest

# Use the pull-through cache prefix:
docker pull 111122223333.dkr.ecr.us-east-1.amazonaws.com/docker-hub/library/nginx:latest
```

The ECR URI format:
`<account>.dkr.ecr.<region>.amazonaws.com/<prefix>/<upstream-path>:<tag>`

For Docker Hub official images, the path includes `library/`:
`docker-hub/library/nginx:latest`

For Docker Hub user images:
`docker-hub/username/repo:tag`

### Cache rule repository management

Pull-through cache creates repositories automatically under the
configured prefix. These repositories:

- Are managed by ECR (you cannot push to them manually).
- Support lifecycle policies (for cache eviction).
- Can be deleted (the next pull will re-create and re-fetch).

```bash
# List repos created by pull-through cache
aws ecr describe-repositories \
  --query 'repositories[?starts_with(repositoryName, `docker-hub/`)]' \
  --region us-east-1

# Apply lifecycle policy to a cache repo (evict old images)
aws ecr put-lifecycle-policy \
  --repository-name docker-hub/library/nginx \
  --lifecycle-policy-text file://cache-lifecycle.json \
  --region us-east-1
```

### Deleting a pull-through cache rule

```bash
aws ecr delete-pull-through-cache-rule \
  --ecr-repository-prefix docker-hub/ \
  --region us-east-1
```

Deleting the rule does NOT delete already-cached images. Existing
cached repos continue to work for pulls but new repos won't be
created for new upstream paths.

## Cost model for replication

### Storage cost

Each replicated image incurs storage cost in BOTH the source and
every destination region.

```text
Cost formula:
  Monthly storage cost = image_size_GB × ECR_rate_per_GB_month × (1 + num_destinations)

  Example: 100 GB of images, 2 destination regions:
    Source:        100 GB × $0.10/GB = $10.00/month
    Destination 1: 100 GB × $0.10/GB = $10.00/month
    Destination 2: 100 GB × $0.10/GB = $10.00/month
    Total: $30.00/month (3x the single-region cost)
```

ECR storage rate (as of 2025): $0.10 per GB-month (varies slightly
by region).

### Data transfer cost

```text
Replication data transfer:
  Source → Destination: AWS inter-region data transfer (~$0.02/GB)

  Pull data transfer:
  ECR → Same-region Lambda/ECS: FREE
  ECR → Cross-region Lambda/ECS: inter-region data transfer
```

### Cost optimization strategies

1. **Apply lifecycle policies in ALL regions:**

```bash
# Lifecycle policy: keep last 30 images, delete the rest
cat > lifecycle.json << 'EOF'
{
  "rules": [
    {
      "rulePriority": 1,
      "description": "Keep last 30 images",
      "selection": {
        "tagStatus": "tagged",
        "countType": "imageCountMoreThan",
        "countNumber": 30
      },
      "action": { "type": "expire" }
    },
    {
      "rulePriority": 2,
      "description": "Delete untagged images older than 7 days",
      "selection": {
        "tagStatus": "untagged",
        "countType": "sinceImagePushed",
        "countUnit": "days",
        "countNumber": 7
      },
      "action": { "type": "expire" }
    }
  ]
}
EOF

# Apply to source
aws ecr put-lifecycle-policy \
  --repository-name my-app \
  --lifecycle-policy-text file://lifecycle.json \
  --region us-east-1

# Apply to EACH destination
aws ecr put-lifecycle-policy \
  --repository-name my-app \
  --lifecycle-policy-text file://lifecycle.json \
  --region us-west-2

aws ecr put-lifecycle-policy \
  --repository-name my-app \
  --lifecycle-policy-text file://lifecycle.json \
  --region eu-west-1
```

2. **Use pull-through cache instead of replication for third-party
   images.** Only one cached copy is stored, not replicated across
   regions.

3. **Replicate only to regions where you deploy.** Remove unused
   destinations.

4. **Clean up orphaned replicas.** When source images are deleted,
   replicas remain. Periodically audit and clean up.

## CloudWatch metrics for replication

### Key metrics

| Metric | Description | Dimension |
|---|---|---|
| `ImageReplicationStatus` | Count by status (Complete, Failed, InProgress) | RepositoryName |
| `RepositoryCount` | Total repositories | (none) |
| `ImageCount` | Total images | (none) |
| `StorageUsed` | Storage in bytes | RepositoryName |

### Monitoring replication health

```bash
# Check for replication failures in the last hour
aws cloudwatch get-metric-statistics \
  --namespace AWS/ECR \
  --metric-name ImageReplicationStatus \
  --dimensions Name=RepositoryName,Value=my-app \
  --start-time $(date -u -v-1H +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 \
  --statistics Sum \
  --region us-east-1

# Create an alarm for replication failures
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
  --alarm-actions "arn:aws:sns:us-east-1:111122223333:ecr-alerts" \
  --region us-east-1
```

## Batch delete protection

### Replicated images cannot be batch-deleted

```bash
# This FAILS on a replicated image:
aws ecr batch-delete-image \
  --repository-name my-app \
  --image-ids imageTag=v1.0 \
  --region us-west-2 \
  --registry-id 111122223333
# Error: "replicated images cannot be deleted via batch-delete"
```

### Correct deletion workflow

```text
1. Delete at source:
   aws ecr batch-delete-image --repository-name my-app \
     --image-ids imageTag=v1.0 --region us-east-1

2. The replica in the destination is now orphaned (standalone).

3. Delete the orphaned replica in each destination:
   aws ecr batch-delete-image --repository-name my-app \
     --image-ids imageTag=v1.0 --region us-west-2

4. Or apply lifecycle policies to automate cleanup in destinations.
```

### Why batch delete is blocked

The block prevents accidental deletion of a replica that would cause
it to be re-replicated from the source on the next push. By requiring
source deletion first, ECR ensures the deletion is intentional and
propagates correctly.

## Expert heuristic: pull-through cache reduces external dependency (moved from SKILL.md)

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
