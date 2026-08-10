# End-to-End Example: ElastiCache Cache Deployment

A walkthrough showing how to use the `elasticache-cache-deployer` skill
from invocation through verification. Mirrors the structured-eval
pattern of shipping a concrete worked example per skill.

---

## Scenario

You are provisioning a production Redis cache with cluster mode enabled.
The cluster needs:

- Engine: Redis (multi-AZ failover, encryption, pub/sub required)
- Cluster mode enabled (3 shards × 1 replica each — Multi-AZ failover)
- Node type: cache.r6g.2xlarge (62.34 GiB nominal; ~31 GiB usable per shard)
- Multi-AZ with automatic failover
- Customer-managed CMK for encryption at rest (alias/prod-cache-kms)
- TLS + AUTH token (token stored in Secrets Manager)
- maxmemory-policy: allkeys-lru (cache workload; disposable data)
- Snapshot retention: 7 days, window 03:00-05:00 UTC
- Maintenance window: sun:05:00-sun:07:00 UTC

Cluster name: `prod-cache`
Region: `us-east-1`
Account: `123456789012`

---

## Step 1 — Invoke the skill

### Option A: Slash command

```
/aws:deploy-elasticache-cache
```

Then paste the requirements.

### Option B: Natural language

```
You: "Provision a production ElastiCache Redis cluster named prod-cache in
      us-east-1. Cluster mode enabled with 3 shards, 1 replica per shard.
      cache.r6g.2xlarge nodes. General cache workload. Customer CMK
      alias/prod-cache-kms. TLS + AUTH. Snapshots 7 days. Subnet group
      prod-cache-subnet. Security group sg-cache123 inbound 6379 from
      sg-app456. Account: 123456789012."
```

### Option C: CLI routing

```bash
node cli/bin/cli.js route "create an elasticache redis cluster"
```

Output:

```
[Phase: Deploy | Skills routed: elasticache-cache-deployer]

Primary route: elasticache-cache-deployer (score: 22)
```

---

## Step 2 — Skill produces the READY_TO_DEPLOY checklist

```text
CACHE: prod-cache
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓] Engine: redis
  [✓] Cluster mode: ENABLED (3 shards)
  [✓] Node type: cache.r6g.2xlarge (62.34 GiB nominal; 31.17 GiB usable per shard; 93.51 GiB total usable)
  [✓] Replicas: 1 per shard (3 total) — Multi-AZ failover
  [✓] Multi-AZ with automatic failover: Enabled
  [✓] Subnet group: prod-cache-subnet (3 AZs)
  [✓] Security group: sg-cache123 (inbound 6379 from sg-app456)
  [✓] Encryption at rest: Enabled (customer CMK alias/prod-cache-kms)
  [✓] Encryption in transit (TLS): Enabled
  [✓] AUTH token: Enabled (stored in Secrets Manager)
  [✓] Parameter group: maxmemory-policy=allkeys-lru (cache semantics)
  [✓] Snapshot retention: 7 days (window 03:00-05:00 UTC)
  [✓] Maintenance window: sun:05:00-sun:07:00
  [✓] Global Datastore: Single-region (us-east-1)
  [✓] ElastiCache Serverless: No
VERIFICATION_COMMANDS:
  aws elasticache describe-replication-groups --replication-group-id prod-cache
  aws elasticache describe-cache-clusters --cache-cluster-id prod-cache-0001 --show-cache-node-info
  aws kms describe-key --key-id alias/prod-cache-kms
```

---

## Step 3 — Provisioning commands

The skill generates the copy-pasteable CLI sequence (from
`references/provisioning-cli-commands.md`):

```bash
# Step 1: Generate AUTH token and store in Secrets Manager
AUTH_TOKEN=$(openssl rand -base64 24)
aws secretsmanager create-secret \
  --name prod-cache-auth-token \
  --secret-string "$AUTH_TOKEN"

# Step 2: Create the parameter group
aws elasticache create-cache-parameter-group \
  --cache-parameter-group-name prod-redis-pg \
  --cache-parameter-group-family redis6.x \
  --description "Production Redis parameter group"

aws elasticache modify-cache-parameter-group \
  --cache-parameter-group-name prod-redis-pg \
  --parameter-name-values \
    ParameterName=maxmemory-policy,ParameterValue=allkeys-lru \
    ParameterName=timeout,ParameterValue=300 \
    ParameterName=tcp-keepalive,ParameterValue=60

# Step 3: Create the replication group
aws elasticache create-replication-group \
  --replication-group-id prod-cache \
  --replication-group-description "Production Redis cluster" \
  --engine redis \
  --cache-node-type cache.r6g.2xlarge \
  --cache-parameter-group-name prod-redis-pg \
  --cache-subnet-group-name prod-cache-subnet \
  --security-group-ids sg-cache123 \
  --num-node-groups 3 \
  --replicas-per-node-group 1 \
  --automatic-failover-enabled \
  --multi-az-enabled \
  --transit-encryption-enabled \
  --at-rest-encryption-enabled \
  --kms-key-id arn:aws:kms:us-east-1:123456789012:alias/prod-cache-kms \
  --auth-token "$AUTH_TOKEN" \
  --snapshot-retention-limit 7 \
  --snapshot-window "03:00-05:00" \
  --maintenance-window "sun:05:00-sun:07:00" \
  --tags Key=Environment,Value=production Key=Workload,Value=cache

# Step 4: Wait for available
aws elasticache wait replication-group-available --replication-group-id prod-cache

# Step 5: CloudWatch alarms
aws cloudwatch put-metric-alarm \
  --alarm-name "prod-cache-cpu-high" \
  --namespace AWS/ElastiCache \
  --metric-name CPUUtilization \
  --dimensions Name=CacheClusterId,Value=prod-cache-0001 \
  --statistic Average --period 60 --threshold 90 \
  --comparison-operator GreaterThan --evaluation-periods 5 \
  --alarm-actions arn:aws:sns:us-east-1:123456789012:cache-alerts

aws cloudwatch put-metric-alarm \
  --alarm-name "prod-cache-swap" \
  --namespace AWS/ElastiCache \
  --metric-name SwapUsage \
  --dimensions Name=CacheClusterId,Value=prod-cache-0001 \
  --statistic Average --period 60 --threshold 0 \
  --comparison-operator GreaterThan --evaluation-periods 1 \
  --alarm-actions arn:aws:sns:us-east-1:123456789012:cache-alerts
```

---

## Step 4 — Post-deployment verification

Run the verification commands from the checklist to confirm every
configuration was applied:

```bash
# Replication group — Status, ClusterEnabled, MemberClusters,
# AutomaticFailover, TransitEncryptionEnabled, AtRestEncryptionEnabled,
# SnapshotRetentionLimit, KmsKeyId
aws elasticache describe-replication-groups --replication-group-id prod-cache

# Per-shard cluster info — CacheNodeType, CacheNodes[*].CacheNodeEndpoint
aws elasticache describe-cache-clusters \
  --cache-cluster-id prod-cache-0001 --show-cache-node-info

# KMS key — KeyState: Enabled, Enabled: true
aws kms describe-key --key-id alias/prod-cache-kms
```

---

## What the skill catches that a naive provisioning misses

| Configuration | Naive provisioning | Skill output | Why the skill is right |
|---|---|---|---|
| Engine choice | Defaults to Memcached for "simplicity" | Redis (encryption + Multi-AZ + persistence needed) | Memcached has no encryption, no failover, no persistence. Migrating Memcached → Redis is a full rewrite. |
| Cluster mode | Picks disabled (simpler) | ENABLED (3 shards) | Cluster mode disabled caps writes at one primary. Migrating disabled → enabled is a full cluster migration. Default enabled for growing workloads. |
| AUTH + TLS together | AUTH without TLS | AUTH + TLS together | AUTH without TLS sends the password in plaintext. The skill refuses to enable AUTH without TLS. |
| Memory budgeting | Quotes spec-sheet memory | 50% of nominal (Redis) | Redis needs ~50% overhead for fork-on-BGSAVE, query buffers, copy-on-write. Plan for 50%; Memcached runs at 90%. |
| maxmemory-policy | Defaults to noeviction | allkeys-lru for cache; noeviction for store | noeviction returns OOM on writes when memory fills — wrong for a cache. allkeys-lru silently evicts — wrong for a session store. |
| Multi-AZ subnet group | Forgets to verify | Confirms subnet group spans >=2 AZs | Multi-AZ requires the replica in a different AZ. A single-AZ subnet group silently blocks Multi-AZ. |
| Snapshot retention | Defaults to 0 | 7-35 days for production | Retention 0 means no point-in-time recovery for Redis. |
| CMK region check | Forgets replica regions | Verifies CMK exists in each Global Datastore region | A missing CMK in a replica region blocks cluster creation there. |

---

## Related artifacts

- **Skill definition:** `skills/elasticache-cache-deployer/SKILL.md`
- **Engine and topology guide:** `skills/elasticache-cache-deployer/references/engine-and-topology.md`
- **Provisioning CLI commands:** `skills/elasticache-cache-deployer/references/provisioning-cli-commands.md`
- **Slash command:** `commands/aws/deploy-elasticache-cache.md`
- **Eval suite:** `skills/elasticache-cache-deployer/evals/evals.json`
- **Legacy test cases:** `skills/elasticache-cache-deployer/eval/test-cases.yaml`
