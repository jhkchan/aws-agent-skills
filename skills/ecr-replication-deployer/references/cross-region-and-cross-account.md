# Cross-Region and Cross-Account Replication — ECR Replication Deployer

Deep reference on ECR registry-level replication configuration
(put-registry-replication-configuration), cross-region replication
patterns (same-account multi-region DR), cross-account replication
(destination registry ID requirements, REPLICATION_DISALLOWED
check), combined replication topologies, and the read-only nature
of replicated images. Loaded on demand by the skill — kept out of
the main SKILL.md body so the provisioning procedure stays
scannable.

## Registry-level replication fundamentals

### The registry is the replication unit

ECR replication is configured at the REGISTRY level, not the
repository level. A single `put-registry-replication-configuration`
call defines all replication rules for the entire registry.

```text
Registry replication scope:
  ├── ALL existing repositories replicate
  ├── ALL future repositories replicate automatically
  ├── Cannot filter by repository name or tag
  └── One API call manages ALL replication
```

This means if you have 100 repositories and only need 5 to
replicate, all 100 will replicate. For selective sharing, use
cross-account repository policies instead.

### The replication configuration API

```bash
# View current replication configuration
aws ecr describe-registry --region us-east-1

# Set replication configuration
aws ecr put-registry-replication-configuration \
  --replication-configuration '{
    "rules": [
      {
        "destinations": [
          {"region": "<dest-region>", "registryId": "<dest-account-id>"}
        ]
      }
    ]
  }' \
  --region us-east-1
```

### Configuration structure

```text
replicationConfiguration:
  rules:
    - rule 1:
        destinations:
          - {region, registryId}  ← destination 1
          - {region, registryId}  ← destination 2
    - rule 2:
        destinations:
          - {region, registryId}  ← destination 3
```

Each rule can have multiple destinations. Multiple rules are
supported for complex topologies.

## Cross-region replication (same account)

### Pattern: multi-region DR

```bash
aws ecr put-registry-replication-configuration \
  --replication-configuration '{
    "rules": [
      {
        "destinations": [
          {"region": "us-west-2", "registryId": "111122223333"},
          {"region": "eu-west-1", "registryId": "111122223333"},
          {"region": "ap-southeast-2", "registryId": "111122223333"}
        ]
      }
    ]
  }' \
  --region us-east-1
```

The `registryId` is the SAME account ID for cross-region replication
within the same account. Images pushed to us-east-1 automatically
appear in all three destination regions.

### Verifying cross-region replication

```bash
# Push an image to source
docker push 111122223333.dkr.ecr.us-east-1.amazonaws.com/my-app:v1.0

# Wait for replication lag (seconds to minutes)

# Verify in destination region
aws ecr describe-images \
  --repository-name my-app \
  --image-ids imageTag=v1.0 \
  --region us-west-2 \
  --registry-id 111122223333 \
  --query 'imageDetails[0].imageTags'

# Pull from destination region
docker pull 111122223333.dkr.ecr.us-west-2.amazonaws.com/my-app:v1.0
```

## Cross-account replication

### Pattern: sharing images with a partner account

```bash
aws ecr put-registry-replication-configuration \
  --replication-configuration '{
    "rules": [
      {
        "destinations": [
          {"region": "us-east-1", "registryId": "999999999999"}
        ]
      }
    ]
  }' \
  --region us-east-1
```

The `registryId` is the DESTINATION account's 12-digit AWS account
ID (different from the source for cross-account).

### Destination account requirements

The destination account must allow incoming replication. By default,
registries allow it. To verify or change:

```bash
# In the DESTINATION account (999999999999)
# Check the registry settings
aws ecr describe-registry --region us-east-1

# The registry must NOT have replication disabled
# If needed, the destination account admin can check the management
# console under ECR > Private registry > Replication settings
```

If the destination has `REPLICATION_DISALLOWED` set, replication
silently fails — no error at configuration time, but images never
appear in the destination.

### Verifying cross-account replication

```bash
# In the DESTINATION account (999999999999)
aws ecr describe-repositories --region us-east-1

# The replicated repos appear with the source account's registry ID
aws ecr describe-images \
  --repository-name my-app \
  --image-ids imageTag=v1.0 \
  --region us-east-1 \
  --registry-id 111122223333

# Pull from the destination account
docker pull 111122223333.dkr.ecr.us-east-1.amazonaws.com/my-app:v1.0
```

**Note:** the image URI uses the SOURCE account's registry ID even
in the destination account. The replicated image is owned by the
source account's registry but accessible in the destination.

## Combined cross-region and cross-account

### Pattern: multi-region, multi-account

```bash
aws ecr put-registry-replication-configuration \
  --replication-configuration '{
    "rules": [
      {
        "destinations": [
          {"region": "us-east-1", "registryId": "999999999999"},
          {"region": "us-west-2", "registryId": "999999999999"},
          {"region": "us-west-2", "registryId": "111122223333"}
        ]
      }
    ]
  }' \
  --region us-east-1
```

This replicates from us-east-1 (111122223333) to:
- Account 999999999999 in us-east-1 (cross-account same-region)
- Account 999999999999 in us-west-2 (cross-account cross-region)
- Account 111122223333 in us-west-2 (same-account cross-region)

## Read-only replica constraints

Replicated images are READ-ONLY in the destination:

```text
Operation                  Source (writable)    Destination (replica)
─────────────────────────  ─────────────────    ──────────────────────
docker push                ALLOWED              DENIED
docker pull                ALLOWED              ALLOWED
docker tag                 ALLOWED              DENIED
batch-delete-image         ALLOWED              DENIED (blocked)
put-lifecycle-policy       ALLOWED              ALLOWED (independent)
delete-repository          ALLOWED              ALLOWED (standalone)
```

**Important:** lifecycle policies CAN be applied to replicated
repositories in the destination — they operate independently from
the source. This is useful for cleaning up old replicas.

## Removing replication

To stop replication, set an empty rules list:

```bash
aws ecr put-registry-replication-configuration \
  --replication-configuration '{"rules": []}' \
  --region us-east-1
```

**Important:** existing replicated images in the destinations are NOT
removed. They become standalone images and must be cleaned up
manually or via lifecycle policy.

## Terraform examples

```hcl
# Cross-region replication
resource "aws_ecr_replication_configuration" "cross_region" {
  replication_configuration {
    rule {
      dynamic "destination" {
        for_each = toset(["us-west-2", "eu-west-1"])
        content {
          region      = destination.value
          registry_id = "111122223333"
        }
      }
    }
  }
}

# Cross-account replication
resource "aws_ecr_replication_configuration" "cross_account" {
  replication_configuration {
    rule {
      destination {
        region      = "us-east-1"
        registry_id = "999999999999"
      }
    }
  }
}
```

## Common replication pitfalls

### Pitfall 1: Expecting per-repo replication

Replication is registry-level. If you only need specific repos to
replicate, use cross-account repository policies:

```bash
# Set a repository policy for selective cross-account access
aws ecr set-repository-policy \
  --repository-name my-app \
  --policy-text file://cross-account-policy.json
```

### Pitfall 2: Destination has replication disabled

Cross-account replication silently fails if the destination account
has `REPLICATION_DISALLOWED`. Always verify with the destination
account admin before configuring cross-account replication.

### Pitfall 3: Assuming replicas are deletable

Replicated images cannot be batch-deleted while linked to the source.
Delete the source image first, then the orphaned replica.

### Pitfall 4: Forgetting lifecycle policies in destinations

Lifecycle policies do NOT replicate. Each region's repos need their
own lifecycle policy. Without them, old replicas accumulate storage
cost.

## Expert heuristic: replication is registry-level (moved from SKILL.md)

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

## Combined cross-region and cross-account configuration (moved from SKILL.md)
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
