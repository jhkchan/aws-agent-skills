# End-to-End Example: MemoryDB Cluster Deployment

A walkthrough showing how to use the `memorydb-cluster-deployer`
skill from invocation through verification. Mirrors the structured-
eval pattern of shipping a concrete worked example per skill.

---

## Scenario

You are provisioning a production MemoryDB for Redis cluster (durable
in-memory database) for a real-time application. The cluster needs:

- Service: MemoryDB (durable in-memory database, NOT ElastiCache cache)
- Engine version: 7.0
- Topology: 3 shards x 1 replica each (Multi-AZ shard-level failover)
- Node type: db.r6g.24xlarge
- TLS at rest + in transit: ON by default
- ACL: named "prod-acl" with users app-rw (read-write) and analytics-ro (read-only)
- Customer-managed CMK: alias/prod-memorydb-kms
- Snapshot retention: 7 days, window 03:00-05:00 UTC
- Maintenance window: sun:05:00-sun:07:00 UTC

Cluster name: `prod-memorydb`
Region: `us-east-1`
Account: `123456789012`

---

## Step 1 — Invoke the skill

### Option A: Slash command

```
/aws:deploy-memorydb-cluster
```

Then paste the requirements.

### Option B: Natural language

```
You: "Provision a production MemoryDB for Redis cluster named
      prod-memorydb in us-east-1. Durable in-memory database — data
      MUST survive node failure. 3 shards with 1 replica each for
      Multi-AZ. db.r6g.24xlarge. Engine 7.0. Customer CMK
      alias/prod-memorydb-kms. Named ACL prod-acl with users app-rw
      and analytics-ro. Snapshots 7 days. Subnet group
      prod-memorydb-subnet spans 3 AZs. Security group sg-memorydb123
      inbound 6379 from sg-app456. Account: 123456789012."
```

### Option C: CLI routing

```bash
node cli/bin/cli.js route "create a memorydb cluster"
```

Output:

```
[Phase: Deploy | Skills routed: memorydb-cluster-deployer]

Primary route: memorydb-cluster-deployer (score: 22)
```

---

## Step 2 — Skill produces the READY_TO_DEPLOY checklist

```text
MEMORYDB: prod-memorydb
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓] Service: MemoryDB (durable in-memory database, NOT ElastiCache cache)
  [✓] Engine version: 7.0
  [✓] Node type: db.r6g.24xlarge (612.30 GiB nominal; 306.15 GiB usable per shard)
  [✓] Shard count: 3 (918.45 GiB total usable)
  [✓] Replicas per shard: 1 (Multi-AZ failover)
  [✓] Multi-AZ with shard-level failover: Enabled
  [✓] Subnet group: prod-memorydb-subnet (spans 3 AZs)
  [✓] Security group: sg-memorydb123 (inbound port 6379 from sg-app456)
  [✓] TLS at rest: Enabled (customer CMK alias/prod-memorydb-kms)
  [✓] TLS in transit: Enabled
  [✓] ACL: prod-acl (users: app-rw, analytics-ro; NOT open-access)
  [✓] Parameter group: default.memorydb-redis7 (maxmemory-policy=volatile-lru)
  [✓] Snapshot retention: 7 days (window: 03:00-05:00 UTC)
  [✓] Maintenance window: sun:05:00-sun:07:00
  [✓] Data tiering: Disabled
  [✓] Multi-Region: Single-region (us-east-1)
VERIFICATION_COMMANDS:
  aws memorydb describe-clusters --cluster-name prod-memorydb --show-shard-node-info
  aws memorydb describe-acls --acl-name prod-acl
  aws memorydb describe-subnet-groups --subnet-group-name prod-memorydb-subnet
  aws ec2 describe-subnets --subnet-ids subnet-0aaa subnet-0bbb subnet-0ccc
  aws kms describe-key --key-id alias/prod-memorydb-kms
```

---

## Step 3 — Provisioning commands

The skill generates the copy-pasteable CLI sequence (from
`references/provisioning-cli-commands.md`):

```bash
# Step 1: Create the subnet group (must span >=2 AZs for Multi-AZ)
aws memorydb create-subnet-group \
  --subnet-group-name prod-memorydb-subnet \
  --description "Multi-AZ subnet group for prod MemoryDB" \
  --subnet-ids subnet-0aaa subnet-0bbb subnet-0ccc

# Step 2: Create users and an ACL (REQUIRED — no open mode in production)
aws memorydb create-user \
  --user-name app-rw \
  --authentication-mode Type=password,Passwords='["SecurePassword123!"]' \
  --access-string "on ~* +@all"

aws memorydb create-user \
  --user-name analytics-ro \
  --authentication-mode Type=password,Passwords='["AnalyticsPassword456!"]' \
  --access-string "on ~* -@all +@read"

aws memorydb create-acl \
  --acl-name prod-acl \
  --user-names app-rw analytics-ro

# Step 3: Create the cluster — TLS on by default, encryption at rest on by default
aws memorydb create-cluster \
  --cluster-name prod-memorydb \
  --description "Production MemoryDB cluster" \
  --node-type db.r6g.24xlarge \
  --acl-name prod-acl \
  --subnet-group-name prod-memorydb-subnet \
  --security-group-ids sg-memorydb123 \
  --num-shards 3 \
  --num-replicas-per-shard 1 \
  --auto-failover-enabled \
  --kms-key-id arn:aws:kms:us-east-1:123456789012:alias/prod-memorydb-kms \
  --snapshot-retention-limit 7 \
  --snapshot-window "03:00-05:00" \
  --maintenance-window "sun:05:00-sun:07:00" \
  --parameter-group-name default.memorydb-redis7 \
  --tags Key=Environment,Value=production Key=Workload,Value=in-memory-db

# Step 4: Wait for available
aws memorydb wait cluster-available --cluster-name prod-memorydb
```

---

## Step 4 — Post-deployment verification

Run the verification commands from the checklist to confirm every
configuration was applied:

```bash
# Cluster — Status, NumberOfShards, ReplicaCount, AutomaticFailover,
# TLSAuthentication, SnapshotRetentionLimit, ACLName
aws memorydb describe-clusters --cluster-name prod-memorydb --show-shard-node-info

# ACL — users, access strings
aws memorydb describe-acls --acl-name prod-acl

# KMS key — KeyState: Enabled, Enabled: true
aws kms describe-key --key-id alias/prod-memorydb-kms
```

---

## What the skill catches that a naive provisioning misses

| Configuration | Naive provisioning | Skill output | Why the skill is right |
|---|---|---|---|
| Service boundary | Provisions MemoryDB for a disposable cache | Redirects to ElastiCache | MemoryDB is a durable database (higher cost). ElastiCache is cheaper for disposable cache data. |
| TLS immutability | Disables TLS for "simplicity" | TLS ON by default (leave it) | Disabling TLS at creation cannot be cleanly re-enabled later. MemoryDB defaults to ON. |
| Named ACL | Uses default `open-access` | Named ACL with least-privilege users | The default `open-access` ACL allows unrestricted read/write. Production MUST use a named ACL. |
| Data tiering | Plans to enable later | `--data-tiering` at creation (one-way door) | Data tiering CANNOT be enabled post-creation without a new cluster + migration. |
| Multi-AZ subnet group | Forgets to verify | Confirms subnet group spans >=2 AZs | Multi-AZ requires the promoted replica in a different AZ. |
| Memory budgeting | Quotes spec-sheet memory | 50% usable rule | Redis needs ~50% overhead for fork-on-snapshot, query buffers, copy-on-write. |
| Shard scaling | Adds replicas to scale writes | Adds shards to scale writes | Replicas scale reads only. Writes scale with shards. |

---

## Related artifacts

- **Skill definition:** `skills/memorydb-cluster-deployer/SKILL.md`
- **Topology and tiering guide:** `skills/memorydb-cluster-deployer/references/topology-and-tiering.md`
- **Provisioning CLI commands:** `skills/memorydb-cluster-deployer/references/provisioning-cli-commands.md`
- **Slash command:** `commands/aws/deploy-memorydb-cluster.md`
- **Eval suite:** `skills/memorydb-cluster-deployer/evals/evals.json`
- **Legacy test cases:** `skills/memorydb-cluster-deployer/eval/test-cases.yaml`
