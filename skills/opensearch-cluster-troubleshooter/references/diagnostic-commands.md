# Diagnostic and pre-flight commands — opensearch-cluster-troubleshooter

Probe command blocks and pre-flight gates, moved verbatim from SKILL.md (load on demand). One command block per diagnostic layer — the failing probe is the positive evidence for ROOT_CAUSE_IDENTIFIED.

## Pre-flight — cluster state and gather-info (describe-domain, AWS Health, _cluster/health)

```bash
# Domain configuration (EngineVersion, ClusterConfig, EBSOptions,
# VPCOptions, SnapshotOptions, ChangeProgressDetails)
aws opensearch describe-domain --domain-name <domain> --output json

# Domain config history (last change to cluster config)
aws opensearch describe-domain-config --domain-name <domain> --output json

# AWS Health (regional events, OpenSearch scheduled maintenance)
aws health describe-events --filter eventStatusCodes=OPEN,UPCOMING \
  --service OPENSEARCH_SERVICE --region us-east-1 --output json

# OpenSearch _cluster/health (the single most informative endpoint)
curl -sS "https://<domain-endpoint>/_cluster/health?pretty" \
  -H "Content-Type: application/json"
```

## Step 2 — Disk watermarks probe commands

```bash
# Per-node disk usage
curl -sS "https://<domain-endpoint>/_cat/allocation?v" \
  -H "Content-Type: application/json"

# CloudWatch FreeStorageSpace (managed-service source of truth)
aws cloudwatch get-metric-statistics --namespace AWS/ES \
  --metric-name FreeStorageSpace \
  --dimensions Name=DomainName,Value=<domain> Name=ClientId,Value=<account> \
  --start-time $(date -d '-1 hour' +%FT%TZ) --end-time $(date +%FT%TZ) \
  --period 300 --statistics Average,Minimum --output json
```

## Step 3 — JVM heap pressure probe commands

```bash
aws cloudwatch get-metric-statistics --namespace AWS/ES \
  --metric-name JVMHeapPressure \
  --dimensions Name=DomainName,Value=<domain> Name=ClientId,Value=<account> \
  --start-time $(date -d '-1 hour' +%FT%TZ) --end-time $(date +%FT%TZ) \
  --period 300 --statistics Average,Maximum --output json

# Per-node heap breakdown
curl -sS "https://<domain-endpoint>/_cat/nodes?v&h=name,heap.percent,ram.percent,node.role" \
  -H "Content-Type: application/json"

# Breaker trip evidence
aws logs filter-log-events \
  --log-group-name /aws/opensearch/domains/<domain>/application-logs \
  --start-time $(date -d '-30 minutes' +%s)000 \
  --filter-pattern '"OutOfMemoryError" OR "circuit_breaking_exception" OR "Old Gen"' \
  --output json
```

## Step 4 — Thread-pool rejection probe commands

```bash
curl -sS "https://<domain-endpoint>/_cat/thread_pool/search?v&h=node_name,name,active,queue,queue_size,rejected,largest" \
  -H "Content-Type: application/json"

curl -sS "https://<domain-endpoint>/_cat/thread_pool/write?v&h=node_name,name,active,queue,queue_size,rejected,largest" \
  -H "Content-Type: application/json"
```

## Step 5 — Cluster red probe commands

```bash
curl -sS "https://<domain-endpoint>/_cluster/health?pretty" -H "Content-Type: application/json"
curl -sS "https://<domain-endpoint>/_cat/shards?v&h=index,shard,prirep,state,unassigned.reason" \
  -H "Content-Type: application/json" | grep UNASSIGNED
curl -sS -X POST "https://<domain-endpoint>/_cluster/allocation/explain?pretty" \
  -H "Content-Type: application/json" -d \
  '{"index": "<index-name>", "shard": <shard-id>, "primary": true}'
```

## Step 7 — Circuit breaker probe command

```bash
curl -sS "https://<domain-endpoint>/_nodes/stats/breaker?pretty" -H "Content-Type: application/json"
```

## Step 9 — Slow query probe commands

```bash
aws cloudwatch get-metric-statistics --namespace AWS/ES \
  --metric-name SearchLatency \
  --dimensions Name=DomainName,Value=<domain> Name=ClientId,Value=<account> \
  --start-time $(date -d '-1 hour' +%FT%TZ) --end-time $(date +%FT%TZ) \
  --period 300 --statistics Average,p99 --output json

aws logs filter-log-events \
  --log-group-name /aws/opensearch/domains/<domain>/index-search-slow-logs \
  --start-time $(date -d '-30 minutes' +%s)000 \
  --filter-pattern '"took[]" OR "query[]"' --output json
```

## Step 10 — Mapping explosion probe command

```bash
curl -sS "https://<domain-endpoint>/<index>/_mapping?pretty" -H "Content-Type: application/json"
```

## Step 11 — Snapshot status probe command

```bash
curl -sS "https://<domain-endpoint>/_snapshot/_status?pretty" -H "Content-Type: application/json"
```

## Step 12a — Upgrade rollback probe command

```bash
aws opensearch describe-domain --domain-name <domain> --output json | \
  jq '.DomainStatus.{EngineVersion, UpgradeProcessing, ChangeProgressDetails}'
```

## Pre-flight safety checks (run before any state-changing CLI)

- **MANDATORY CONFIRMATION GATE.** Before any state-changing operation
  (`DELETE /<index>`, `POST /<index>/_close`, `PUT _cluster/settings`,
  `PUT _all/_settings`, `DELETE /_snapshot/...`,
  `POST /<index>/_forcemerge`), emit and await operator approval.
- **Read-only first.** Every probe in the diagnostic tree is
  read-only. Do not perform state-changing operations as diagnostic
  probes.
- **`DELETE /<index>`** is irreversible. Enumerate the index list
  explicitly; never use wildcards in `DELETE /logs-*`.
- **Force-clearing the flood-stage block** is safe ONLY after disk
  is below 95%. Confirm disk usage first.
- **Cluster scaling** triggers a blue/green deployment (30+ minutes).
- **Version upgrade** triggers validation. Confirm cluster health is
  green and heap < 75% first.
- **Bulk remediation batch limit.** Batch state-changing operations
  into groups of at most 5 indices; emit a single CONFIRM per batch.
