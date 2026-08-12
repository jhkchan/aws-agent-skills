# ECR Lifecycle, Replication, and Registry Reference Guide

Supplementary reference for the ECR Push/Pull Troubleshooter skill.
Loaded on-demand when a diagnostic needs lifecycle-policy rule
evaluation semantics, cross-region replication configuration, or
registry-level settings (encryption, alias, pull-through cache).

## Lifecycle policy evaluation

Lifecycle policies automate image cleanup. Misconfiguration is the
most common cause of images vanishing without a manual delete.

### Rule evaluation order

Rules evaluate top to bottom (lowest `rulePriority` first). **The
FIRST matching rule wins** — its `action` is applied and no further
rule is evaluated for that image. This is critical: a broad `expire`
rule placed above a narrower `keep`-intent rule will delete images
the lower rule would have protected.

### Rule structure

```json
{
  "rulePriority": 1,
  "selection": {
    "tagStatus": "tagged" | "untagged" | "any",
    "tagPrefixList": ["v", "prod-"],
    "countType": "imageCountMoreThan" | "sinceImagePushed",
    "countNumber": 5,
    "countUnit": "days"
  },
  "action": {"type": "expire"}
}
```

### Selection field semantics

| Field | Values | Effect |
|---|---|---|
| `tagStatus` | `tagged` | Rule applies only to images with at least one tag |
| | `untagged` | Rule applies only to images with no tags |
| | `any` | Rule applies to all images regardless of tags |
| `tagPrefixList` | `["prod-", "v"]` | Filters `tagged` images to those with a tag starting with a prefix |
| `countType` | `imageCountMoreThan` | Rule matches when the repository has more than `countNumber` matching images |
| | `sinceImagePushed` | Rule matches images pushed more than `countNumber` `countUnit` ago |
| `countNumber` | integer | Threshold for the count type |
| `countUnit` | `days` (only valid unit for `sinceImagePushed`) | Unit for time-based rules |

### Common lifecycle footguns

| Pattern | Consequence |
|---|---|
| `tagStatus: any, count: 3` at priority 1 | Deletes the 4th+ newest image regardless of tags — catches untagged and tagged alike |
| `tagStatus: untagged, count: 1` above a `tagStatus: tagged` rule | Any image that loses its last tag (e.g., re-tagged) is immediately deleted |
| Broad `expire` above a `keep`-intent rule | The `keep` rule never fires because the `expire` rule matches first |
| Very short `sinceImagePushed: 1 day` | Images older than 24 hours vanish — surprising for release tags that should persist |

### Lifecycle policy preview

Always dry-run a new or modified policy before applying:

```bash
aws ecr start-lifecycle-policy-preview \
  --repository-name <repo> \
  --lifecycle-policy-text file://policy.json \
  --output json --profile <p>

aws ecr get-lifecycle-policy-preview \
  --repository-name <repo> --output json --profile <p> | \
  jq '.previewResults[] | select(.action.type == "expire")'
```

The preview returns the list of image digests that WOULD be deleted.
Review this list before running `put-lifecycle-policy`.

## Cross-region replication

Cross-region replication copies images from a source registry to one
or more destination registries automatically after push.

### Configuration scope

Replication is configured at the **source registry** level (not per
repository). A single `put-replication-configuration` call applies to
every repository in the source registry.

```bash
aws ecr put-replication-configuration \
  --replication-configuration '{
    "rules": [{
      "destinations": [{
        "region": "eu-west-1",
        "registryId": "111111111111"
      }]
    }]
  }' --region us-east-1 --profile <p>
```

### Replication semantics

| Property | Behaviour |
|---|---|
| Scope | Per-source-registry (all repositories) |
| Latency | Asynchronous — typically seconds to minutes after push |
| Consistency | Eventual; a pull in the destination region before replication completes fails with `manifest unknown` |
| Cross-account | The destination `registryId` can be a different account; the destination account must have a replication permission (the ECR service handles cross-account via a service-linked role) |
| Deletion | Replication does NOT propagate deletes; deleting an image in the source does not delete the replica |
| Overwrite | Re-pushing the same tag in the source triggers re-replication of the new digest |

### Diagnosing replication failures

```bash
aws ecr describe-registry --region <source> --output json --profile <p>
aws ecr get-replication-configuration --region <source> --output json --profile <p>
aws ecr describe-images --repository-name <repo> --region <dest> --output json --profile <p>
```

If no replication rule covers the destination, no replication occurs.
If a rule exists and the image is missing minutes after push, check
AWS Health for replication service degradation.

## Registry settings

### Encryption configuration

| `encryptionType` | Key | Caller KMS permission needed? |
|---|---|---|
| `AES256` | ECR-managed key (S3-style) | No — transparent to the caller |
| `KMS` | Customer-managed CMK (specified by `kmsKey`) | Yes — pusher: `kms:GenerateDataAccess`; puller: `kms:Decrypt` |

For `KMS` encryption, the key policy must also grant the ECR service
principal (`ecr.<region>.amazonaws.com`) the following on the key:

- `kms:CreateGrant`
- `kms:DescribeKey`
- `kms:Decrypt`
- `kms:GenerateDataAccess`

Without the key-policy side, ECR cannot encrypt/decrypt on the caller's
behalf even if the caller's IAM policy allows the KMS actions.

### Registry alias (ECR Public)

ECR Public registries have aliases: `public.ecr.aws/<alias>/<repo>`.

```bash
aws ecr-public describe-registries --output json --profile <p> | \
  jq '.registries[] | {registryId, aliases: [.aliases[] | .name], primaryAlias}'
```

Each alias is globally unique and owned by one account. A collision
(your intended alias is owned by another account) produces a
`REGISTRY_ALIAS_MISMATCH`-class error. Verify alias ownership before
pushing.

## Pull-through cache

Pull-through cache rules allow ECR Private to cache images from
upstream registries on first pull.

### Configuration

```bash
aws ecr create-pull-through-cache-rule \
  --ecr-repository-prefix <prefix> \
  --upstream-registry-url <upstream-url> \
  --registry-id <registry-id> \
  --region <region> --profile <p>
```

### Supported upstream registries

| Upstream | URL | Credential source |
|---|---|---|
| ECR Public | `public.ecr.aws` | None (public pulls) |
| Docker Hub | `registry-1.docker.io` | Secrets Manager secret (to avoid rate limits) |
| Quay | `quay.io` | Secrets Manager secret (private repos) |
| GitHub Container Registry | `ghcr.io` | Secrets Manager secret |

### Common misconfigurations

| Pattern | Cause |
|---|---|
| `ecrRepositoryPrefix` does not match the local cached repo name | Pull never hits the rule; image is never cached |
| Upstream secret missing or stale | `unable to pull from upstream: unauthorized` |
| Local registry is KMS-encrypted; caller lacks `kms:Decrypt` | `KMS.AccessDeniedException` on the pull-through write |
| Upstream rate limit (Docker Hub anonymous) | Pull loops; upgrade to authenticated upstream |

## Image tag immutability

| Setting | Behaviour |
|---|---|
| `MUTABLE` (default) | A tag can be overwritten; each push replaces the digest the tag points to |
| `IMMUTABLE` | A tag cannot be overwritten; first push succeeds, subsequent pushes of the same tag fail with `image tag already exists and is immutable` |

Immutability is **per-repository**, not per-registry. Changing one
repository does not affect any other.

Switching back from `IMMUTABLE` to `MUTABLE` and then re-pushing lets
a tag float again. Past overwrites (done while MUTABLE) are not
retroactively validated.

```bash
aws ecr put-image-tag-mutability \
  --repository-name <repo> \
  --image-tag-mutability IMMUTABLE | MUTABLE \
  --profile <p>
```

## Image size limits

| Property | Limit |
|---|---|
| Compressed image (total) | 10 GiB |
| Compressed layer (single) | 10 GiB |
| Image manifest size | 4 MiB |
| Tag length | 128 chars |
| Repository name length | 256 chars |

The 10 GiB cap is on the compressed size ECR stores, not the
uncompressed size docker reports. For a rough check, compare docker's
reported size to the threshold with a 1.5-2x margin (general images
compress well; already-compressed data like ML model weights does
not).

Recommended image sizes by workload:

- Light API handler: < 200 MB compressed
- Mid-tier (framework + SDK): 200-500 MB
- Heavy (Spring Boot, Java framework): 500 MB-1 GB
- Very heavy (ML inference bundled): 1-3 GB; cold-start pull cost is real
- Above 3 GB: extract heavy bits to a Layer or EFS
