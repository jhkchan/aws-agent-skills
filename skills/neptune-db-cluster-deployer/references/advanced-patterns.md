# Neptune DB Cluster Deployer — Advanced Patterns

Provisioning-time misconceptions, the configuration dependency graph, and recent
AWS features moved verbatim from SKILL.md. Load on demand.

## Three misconceptions that dominate Neptune misdesign

Three misconceptions dominate Neptune misdesign at provisioning time:

- **"Neptune Analytics is just a bigger Neptune DB."** It is not.
  Neptune DB is a transactional (OLTP) graph database with a
  writer-replica cluster, Multi-AZ failover, and Gremlin/SPARQL/
  openCypher endpoints. Neptune Analytics is a separate analytics
  (OLAP) service for graph algorithms on large datasets with its own
  API (`create-graph`), no writer/replica split, and no Gremlin
  transactions. They share query languages but not the data plane.
  Pick the service before any other decision — this skill only
  provisions Neptune DB.

- **"Set encryption at rest after the cluster is running."** Neptune
  encryption at rest is **immutable**: it MUST be set at creation via
  `--storage-encrypted` (and an optional customer CMK via
  `--kms-key-id`). Adding it later requires snapshot → restore into a
  new encrypted cluster. Same for TLS — `neptune_enforce_ssl=1` in
  the parameter group applied at creation locks the cluster to TLS-only.

- **"A single instance is fine for production."** Neptune's
  writer-only topology has no failover. Multi-AZ requires at least one
  reader instance in a different AZ; promotion takes ~30 seconds. The
  minimum production topology is 1 writer + 1 reader across two AZs,
  with `--deletion-protection` on the cluster.

## Configuration dependency graph (novel heuristic)

Neptune configurations are NOT independent. Many are immutable after
creation, others silently downgrade. Use this graph both to sequence
provisioning and to debug "why can't I add this?" later.

| Configuration | Hard dependencies (API error without) | Silent failure / immutability | Enables downstream |
|---|---|---|---|
| Engine version (`1.3.x.x`) | none — `create` argument | engine upgrades apply in maintenance window; rolling with brief endpoint flapping | Gremlin 3.7+, openCypher, server-side plan cache |
| Instance class | none — `create` argument | changeable via `modify-db-instance` with rolling reboot | memory budget, CPU for traversal depth |
| Writer + reader replicas | DB subnet group spanning >=2 AZs (Multi-AZ) | writer-only = NO failover; promotion needs >=1 reader in different AZ | Multi-AZ, read scaling, failover |
| Storage / IOPS | set at cluster create | **IMMUTABLE** — change requires snapshot/restore | throughput for write-heavy graphs |
| Encryption at rest (KMS) | `--storage-encrypted` + optional `--kms-key-id` at creation | **CANNOT be added post-creation** without snapshot/restore | compliance (HIPAA, PCI, SOC2) |
| TLS / neptune_enforce_ssl | parameter group applied at creation | changing requires instance reboot; mixed TLS is messy | TLS-only clients, sniffing defense |
| IAM database auth | `--enable-iam-database-authentication` at creation | can be enabled post-create via modify but triggers rolling reboot; non-IAM auth still works in parallel unless disabled | token-based access |
| DB subnet group | VPC + >=1 subnet; >=3 AZs for Multi-AZ | subnets CANNOT be removed once added; only added | VPC-only addressing |
| Security group | VPC | port 8182 inbound from application SG | network isolation |
| Parameter group | none — `create` argument | parameter changes apply on next reboot | neptune_enforce_ssl, neptune_query_timeout, labs modes |
| Bulk load from S3 | S3 bucket + IAM role with `neptune-load` trust + `s3:GetObject`; source in same region | concurrent loads on the same cluster conflict; loader is idempotent per `load_id` | initial ingest |
| Neptune Streams | `neptune_streams=1` in parameter group + (recommended) Kinesis/Lambda consumer | enabling/disabling requires instance reboot; stream records resume after reboot | change data capture, replication |
| Snapshot (automated) | `--backup-retention-period > 0` at cluster create | restore creates a NEW cluster; snapshot is cluster-scoped | point-in-time recovery |
| Deletion protection | `--deletion-protection` at cluster create | with protection on, `delete-db-cluster` fails until disabled | accidental-delete defense |

**The immutable rows are the ones a baseline model misses.** Engine
version (rolling), storage config, encryption at rest, and VPC/subnet
placement are decided at creation time. The procedure below forces an
explicit decision on each before the `create-db-cluster` call.

**Cross-dependency gotchas:**
- Enabling `neptune_enforce_ssl=1` on an existing cluster requires a
  rolling instance reboot — plaintext clients drop. Enable at creation.
- IAM auth and password auth can coexist; to enforce IAM-only, do NOT
  set a password and rely on IAM tokens. Mixed mode is a common source
  of "why did this auth succeed?" confusion.
- The Neptune Loader only reads S3 buckets in the SAME region as the
  cluster. Cross-region loads require replicating the bucket first.
- A Multi-AZ cluster with only 1 instance (writer) has NO failover
  target. The cluster endpoint resolves to the writer; on writer loss
  with no readers, the cluster is unavailable until a new instance is
  promoted.

## Recent AWS features (2023-2026)

**Recent AWS features (2023-2026):**
- **Neptune Analytics (2023-2024):** Separate OLAP graph service with
  built-in algorithms (PageRank, BFS). NOT this skill — separate
  `aws graph` API. Pair with Neptune DB for batch analytic pipelines.
- **openCypher improvements (2023-2024):** Server-side planning and
  caching improve repeat-query latency ~30%. Use the latest engine
  version.
- **Engine version 1.3.x.x (rolling):** Gremlin 3.7+ support, better
  SPARQL federation. Pin the major version explicitly in production;
  do not use "latest".
- **Graviton (r6g) instance classes (2022-2024):** ~15% better
  price/performance over r5. Default to Graviton for new clusters.
- **IAM database auth enhancements (2023-2024):** Fine-grained
  `neptune-db:*` actions for query/type-level RBAC.
