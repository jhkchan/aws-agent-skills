# Worked Examples — OpenSearch Migration Operator
Secondary worked examples, moved verbatim from SKILL.md.

### Worked example — migration BLOCKED (ES-only plugin)
```text
OPERATION: assess
VERDICT: BLOCKED
TARGET: legacy-search-cluster (ES 6.8 -> OpenSearch 2.11)
PRE_CHECKS:
  - [PASS] Domain status is Active
  - [PASS] Cluster health is green
  - [FAIL] Source version Elasticsearch_6.8 is NOT eligible for direct in-place upgrade. Must upgrade to ES 7.10 first, or use new-cluster + reindex migration path.
  - [FAIL] ES-only plugin x-pack-ml is installed. No direct OpenSearch equivalent (OpenSearch anomaly detection uses a different API). Must remove and reconfigure before migration.
STEPS: (none — pre-checks failed)
POST_VERIFY: (none)
ENDPOINT: N/A — migration blocked
CLIENT_NOTES:
  - BLOCKED: Remediation required before migration can proceed.
  - Option A: Upgrade ES 6.8 to 7.10 (if supported), remove x-pack-ml, then migrate to OpenSearch.
  - Option B: Provision new OpenSearch 2.x cluster, reindex from remote, reconfigure ML jobs as OpenSearch anomaly detectors.
  - Reindex-from-remote requires network connectivity between the ES 6.8 domain and the new OpenSearch domain.
```

### Worked example — COMPLETED (blue/green migration verified)
```text
OPERATION: blue-green
VERDICT: COMPLETED
TARGET: prod-search-cluster (ES 7.10 -> OpenSearch 2.11)
PRE_CHECKS:
  - [PASS] (all pre-checks passed before execution)
STEPS:
  1. Pre-upgrade snapshot taken at 2026-08-10T08:00:00Z
  2. aws opensearch update-domain-config executed at 2026-08-10T08:15:00Z
  3. Blue/green deployment completed at 2026-08-10T09:45:00Z (90 min)
POST_VERIFY:
  - [PASS] Cluster health is green
  - [PASS] Document counts match (45 indices, 2.1B docs)
  - [PASS] Index mappings preserved correctly
  - [PASS] Application search queries return correct results (100% match)
  - [PASS] compatible=40 mode works for elasticsearch-py 7.17 clients
  - [PASS] Snapshot repository s3-migration-repo is registered
  - [PASS] No red shards or unassigned replicas
  - [PASS] OpenSearch plugins confirmed: analysis-icu, analysis-phonetic, ingest-attachment
ENDPOINT: https://search-prod-search-cluster.us-east-1.es.amazonaws.com (unchanged)
CLIENT_NOTES:
  - Blue/green migration completed (90 min). compatible=40 is active for ES 7.x clients.
  - Plan to migrate client libraries to opensearch-* within 3-6 months.
  - Test neural search and vector DB features available in OpenSearch 2.11.
```

### Worked example — snapshot setup and migration (READY)
```text
OPERATION: snapshot-setup
VERDICT: READY
TARGET: staging-search-cluster (ES 7.10 -> OpenSearch 2.11)
PRE_CHECKS:
  - [PASS] Domain status is Active
  - [PASS] Cluster health is green
  - [PASS] S3 bucket migration-snapshots exists and is writable
  - [PASS] IAM role OpenSearchSnapshotRole has s3:PutObject, s3:GetObject, s3:ListBucket
  - [PASS] No existing repository named s3-migration-repo
STEPS:
  1. Register S3 repo: PUT _snapshot/s3-migration-repo {"type":"s3","settings":{"bucket":"migration-snapshots","region":"us-east-1","base_path":"staging-migration","role_arn":"arn:aws:iam::111111111111:role/OpenSearchSnapshotRole"}}
  2. Verify: POST _snapshot/s3-migration-repo/_verify
  3. Take full snapshot: PUT _snapshot/s3-migration-repo/staging-full-snapshot?wait_for_completion=true {"indices":"*","ignore_unavailable":true,"include_global_state":false}
  4. Confirm: GET _snapshot/s3-migration-repo/staging-full-snapshot
POST_VERIFY: (pending execution)
ENDPOINT: N/A (snapshot setup — no client impact)
CLIENT_NOTES: N/A (snapshot setup — no client impact)
```
