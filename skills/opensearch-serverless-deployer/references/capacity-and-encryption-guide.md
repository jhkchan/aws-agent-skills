# Capacity (OCU), Encryption, and Security Reference

Supplementary reference for the OpenSearch Serverless Deployer skill.
Use when sizing OCU capacity, configuring KMS encryption, or planning
standby replicas and VPC access.

## OCU (OpenSearch Compute Units)

OCU is the unit of compute capacity. Each OCU provides approximately:
- 6 GiB of RAM
- Equivalent of 1 vCPU of dedicated compute
- Up to ~120 GB of hot storage (varies by index format)

### OCU types

| Type | Purpose | Minimum floor |
|---|---|---|
| Indexing OCU | Ingests, parses, and indexes documents | 2 (production) |
| Search OCU | Serves queries and aggregations | 2 (production) |

The floor is billed continuously regardless of workload. Auto-scaling adds
OCUs up to the configured ceiling (`MaxIndexingCapacityInOCU`,
`MaxSearchCapacityInOCU`) and removes them after a cooldown.

### Auto-scaling behavior

| Condition | Trigger | Action |
|---|---|---|
| Scale up | CPU or memory > 70% for 5 minutes | Add 1 OCU (indexing or search independently) |
| Scale down | CPU and memory < 30% for 30 minutes | Remove 1 OCU (never below floor) |

Scaling is independent for indexing and search — a write-heavy workload
scales indexing OCUs while search OCUs stay at floor.

### Sizing rules of thumb

| Workload | Ingest rate | Query rate | Recommended floor |
|---|---|---|---|
| Low (dev/staging) | < 500 docs/sec | < 50 queries/sec | 2 indexing + 2 search (4 OCU) |
| Medium (production) | 500-2000 docs/sec | 50-200 queries/sec | 4 indexing + 4 search (8 OCU) |
| High (enterprise) | 2000-5000 docs/sec | 200-500 queries/sec | 8 indexing + 8 search (16 OCU) |

Add 1 search OCU per ~50 additional queries/sec beyond the baseline.
Add 1 indexing OCU per ~500 additional docs/sec beyond the baseline.

### Standby replicas

| Setting | Effect | Cost impact |
|---|---|---|
| `ENABLED` | Warm replica in second AZ; automated failover on AZ failure | Doubles effective OCU count (and cost) |
| `DISABLED` | Single AZ; no failover | Baseline cost only |

For production, ALWAYS enable standby replicas. The cost doubling is the
price of availability. Dev/staging may disable with documented justification.

### Cost estimation (us-east-1, 2025)

| Configuration | OCU count | Monthly cost |
|---|---|---|
| 4 OCU floor, no standby | 4 | 4 x $0.204 x 720 = $588 |
| 4 OCU floor, with standby | 8 (4 primary + 4 standby) | 8 x $0.204 x 720 = $1,175 |
| 8 OCU floor, with standby | 16 (8 + 8) | 16 x $0.204 x 720 = $2,351 |
| Storage (beyond OCU allocation) | per GB | $0.024/GB-month |
| VPC endpoint | per endpoint + data | $0.01/hr + $0.01/GB processed |

## Encryption (KMS)

### Encryption policy

The encryption security policy maps a collection name pattern to a KMS key.
It MUST exist before collection creation.

```json
{
  "Rules": [
    {"ResourceType": "collection", "Resource": ["collection/prod-*"]}
  ],
  "KmsKeyArn": "arn:aws:kms:us-east-1:111111111111:key/abc-123"
}
```

### KMS key requirements

| Requirement | Detail |
|---|---|
| Key spec | MUST be `SYMMETRIC_DEFAULT` |
| Key usage | `ENCRYPT_DECRYPT` |
| Key policy | Grant `kms:Decrypt`, `kms:DescribeKey`, `kms:CreateGrant` to `opensearch-serverless.amazonaws.com` |
| Cross-account | If the key is in a different account, the key policy must allow the collection's account |

### AWS-owned key vs customer-managed key

| Dimension | AWS-owned key | Customer-managed KMS |
|---|---|---|
| CloudTrail key usage | Not visible | Visible (Decrypt, GenerateDataKey) |
| Key rotation | Managed by AWS | Configurable (annual automatic) |
| Cross-account access | Not possible | Configurable via key policy |
| Cost | Free (included) | $1/key/month + per-API-call |
| Recommendation | Dev/staging | Production (compliance, auditability) |

### Immutability

The KMS key is bound at collection creation and **cannot be changed**. To
switch keys:
1. Create a new encryption policy with the new key.
2. Create a NEW collection matching the new policy.
3. Reindex data from the old collection to the new.
4. Delete the old collection (data loss if not reindexed).

## Network security

### Network policy types

| Access type | Configuration | Use case |
|---|---|---|
| Public | `"AllowFromPublic": true` | Internet-facing applications |
| VPC-only | `"SourceVPCEs": ["vpce-xxx"]` | Private applications, compliance |
| Hybrid | Both public and VPC | Public collection + VPC dashboards |

### VPC endpoint

```bash
aws opensearchserverless create-vpc-endpoint \
  --name prod-vpce \
  --vpc-id vpc-abc123 \
  --subnet-ids subnet-aaa subnet-bbb \
  --security-group-ids sg-abc123 \
  --collection-endpoints <endpoint>
```

Requirements:
- Subnet IDs MUST be in the specified VPC.
- Security group MUST allow inbound 443 from the application subnet.
- VPC endpoint takes 5-15 minutes to become AVAILABLE.
- Private DNS (2025): the collection endpoint resolves via Route 53
  resolver without custom DNS configuration.

## Data access model

OpenSearch Serverless uses **data access policies** (IAM principals), NOT
resource-based policies (like managed OpenSearch).

```json
[
  {
    "Permission": ["aoss:CreateCollectionItems", "aoss:DescribeCollectionItems", "aoss:UpdateCollectionItems"],
    "Principal": ["arn:aws:iam::111111111111:role/AdminRole"]
  },
  {
    "Permission": ["aoss:ReadDocuments", "aoss:DescribeCollectionItems"],
    "Principal": ["arn:aws:iam::111111111111:role/SearchRole"]
  },
  {
    "Permission": ["aoss:WriteDocuments"],
    "Principal": ["arn:aws:iam::111111111111:role/IngestRole"]
  }
]
```

The collection creator does NOT automatically get access. A data access
policy MUST be created — without it, no one can index or query documents.

### Permission levels

| Permission | Scope |
|---|---|
| `aoss:CreateCollectionItems` | Create indexes within the collection |
| `aoss:UpdateCollectionItems` | Modify index settings/mappings |
| `aoss:DescribeCollectionItems` | Read collection/index metadata |
| `aoss:WriteDocuments` | Index, update, delete documents |
| `aoss:ReadDocuments` | Search, get, mget documents |
| `aoss:DeleteCollectionItems` | Delete indexes within the collection |

## SAML authentication

### SAML metadata

For IAM Identity Center, use the application SAML metadata URL:

```bash
aws opensearchserverless update-collection \
  --id <collection-id> \
  --saml-options '{
    "Metadata": {"URL": "https://identity-center.amazonaws.com/saml/metadata/abc"},
    "GroupAttribute": "department",
    "SessionTimeout": 60
  }'
```

For external IdPs (Okta, Azure AD), provide the metadata XML or URL
directly.

### Requirements

- The metadata URL MUST be reachable from the OpenSearch Serverless service.
- `GroupAttribute` maps SAML groups to OpenSearch Serverless roles for
  index-level access control.
- `SessionTimeout` is in minutes (max 480 / 8 hours).
- SAML and IAM data access policies are complementary — SAML controls
  dashboard access, IAM controls API access.
