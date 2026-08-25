# Diagnostic Commands — OpenSearch Migration Operator
Diagnostic and pre-flight command listings, moved verbatim from SKILL.md.

## Pre-flight: domain metadata gate
**Live-account pre-flight (skip if offline plan audit):**
1. `aws opensearch describe-domain --domain-name <name>` — confirm
   domain status, EngineVersion, ClusterConfig (instance type, node
   count, dedicated masters), EBSOptions, EncryptionAtRestOptions,
   VPCOptions, SnapshotOptions.
2. `aws es describe-elasticsearch-domain --domain-name <name>` (for
   legacy ES domains) — capture the ES version, cluster config, and
   snapshot configuration.
3. `curl -s https://<endpoint>/ _cluster/health` — cluster status
   (green/yellow/red), number of nodes, active shards, relocating
   shards.
4. `curl -s https://<endpoint>/ _cat/indices?v` — index list, document
   counts, store sizes.
5. `curl -s https://<endpoint>/ _cat/plugins?v` — installed plugins.
6. `curl -s https://<endpoint>/ _nodes/plugins` — detailed plugin info
   per node.
7. `curl -s https://<endpoint>/ _snapshot` — registered snapshot
   repositories.
8. `curl -s https://<endpoint>/ _mapping` — index mappings for
   compatibility assessment.

## Pre-flight safety checks (run before any migration CLI)
- **MANDATORY CONFIRMATION GATE.** Before any state-changing migration
  operation (`update-domain-config`, `_snapshot`, `_restore`, `_reindex`),
  emit the CONFIRM prompt. Do NOT execute until the operator confirms.
- **Snapshot before upgrade.** Take a full snapshot to the S3 repository
  before any in-place upgrade. This is the rollback path.
- **Verify snapshot repository.** `POST _snapshot/<repo>/_verify` must
  show all data nodes reporting success.
- **Check cluster health.** Cluster must be `green` (or `yellow` with
  documented reason). `red` means data loss risk — BLOCK.
- **Inventory plugins.** `_cat/plugins` must show no ES-only commercial
  plugins for in-place upgrade path.
- **Test network connectivity.** For reindex-from-remote, verify the
  target can reach the source endpoint on port 443.
- **Verify IAM permissions.** The migration role needs `es:ESHttp*` or
  `opensearch:ESHttp*` plus `s3:*` on the snapshot bucket.
- **Schedule during low-traffic windows.** Blue/green deployment causes
  degraded performance (30-120 minutes). Plan for off-peak.
- **One domain per CONFIRM gate.** Do NOT batch multiple domain
  migrations — a systematic issue cascades across domains.
