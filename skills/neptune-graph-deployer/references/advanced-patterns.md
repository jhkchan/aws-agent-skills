# Neptune Graph Deployer — Advanced Patterns

Provisioning misconceptions, the configuration dependency graph, the sizing
heuristic, and recent features moved verbatim from SKILL.md. Load on demand.

## Three misconceptions that dominate Neptune misdesign

Three misconceptions dominate Neptune misdesign at provisioning time:

- **"Instance storage is just disk — IOPS don't matter for a graph
  database."** They DO. Neptune uses instance storage for the graph
  working set. Graph traversals (especially multi-hop Gremlin queries)
  are I/O-intensive. Undersized instance storage or insufficient
  provisioned IOPS cause query timeouts and high latency. Choose the
  instance type based on BOTH memory (graph working set fit) AND IOPS
  (traversal concurrency).

- **"Read replicas scale writes too."** They do NOT. Neptune read
  replicas serve only read queries (Gremlin traversals, SPARQL SELECT).
  ALL writes go to the primary instance. If write throughput is the
  bottleneck, a larger primary instance type is needed — not more
  replicas. Read replicas solve read concurrency, not write throughput.

- **"Gremlin and SPARQL require separate clusters."** They do NOT.
  Neptune supports BOTH query languages on the same cluster. Gremlin
  queries the property graph; SPARQL queries the RDF view of the same
  data (if the RDF feature is enabled). Choose the query language based
  on the use case, not the cluster.

## Configuration dependency graph (novel heuristic)

Neptune configurations are NOT independent. Encryption must be enabled
at creation. Parameter groups control SSL enforcement and query
timeouts. Neptune Streams must be explicitly enabled. Global Database
requires matching engine versions. Use this graph to sequence
provisioning.

| Configuration | Hard dependencies | Silent failure / immutability | Enables downstream |
|---|---|---|---|
| Subnet group | >= 2 AZs (multi-AZ); same VPC | Cross-VPC subnets rejected | cluster creation |
| Security group | Port 8182 (Neptune default) | No ingress = client timeout | client connectivity |
| DB cluster parameter group | Created before cluster | neptune_enforce_ssl is static (requires instance reboot) | SSL enforcement |
| Cluster (primary) | Subnet group + parameter group + SG | Encryption at rest CANNOT be toggled after creation | graph storage |
| Read replicas | Cluster exists; replicas in different AZs | Replicas do NOT help write throughput | read scaling |
| IAM database authentication | Must be enabled at cluster creation | Cannot toggle without recreating | IAM-based access |
| Encryption at rest (KMS) | KMS key exists; set at creation | CANNOT enable on existing cluster | compliance |
| Neptune Streams | Streams parameter set to TRUE in parameter group | Stream records exist only after enablement | change capture |
| Neptune ML | S3 bucket for model artifacts; SageMaker IAM role | ML inference endpoint adds latency to queries | graph ML |
| Global Database | Primary cluster in region A; same engine version | Secondary is read-only until failover | cross-region DR |
| Auto-scaling read replicas | Cluster exists; scaling policy defined | Min/max must be within replica limits (0-15) | read elasticity |
| Bulk loader | Cluster exists; S3 bucket with source data; IAM role | Loader is for initial/batch loads, not streaming | data ingestion |

**The encryption-at-creation row is the one a baseline model misses.**
Like RDS and ElastiCache, Neptune encryption at rest is creation-time-
only. The procedure forces an explicit encryption decision before
cluster creation.

**Cross-dependency gotchas:**
- IAM database authentication must be enabled at cluster creation. It
  cannot be toggled on afterward.
- `neptune_enforce_ssl` is a static parameter — changing it requires an
  instance reboot to take effect.
- Neptune Streams must be explicitly enabled in the parameter group
  (`neptune_streams = 1`). Stream records only start flowing after
  enablement — past changes are NOT captured.
- Read replica auto-scaling adds replicas based on CPU utilization, but
  replicas take minutes to become available. Spikes can still cause
  timeouts during the scale-out period.
- Global Database requires matching engine versions. The secondary
  cluster is read-only until a planned failover.
- Bulk loader is for batch ingestion, not continuous streaming. For
  streaming, use Neptune Streams consumer pattern.

## Expert heuristic: instance storage vs IOPS + read replica scaling + Stream filter patterns

A baseline model says "create a Neptune cluster with a few replicas."
The correct heuristic matches instance storage type and IOPS to the
graph working set size and traversal concurrency, scales read replicas
based on Gremlin traversal patterns, and configures Neptune Streams
with appropriate filter patterns.

```text
Instance type selection (IOPS + storage):

  Graph working set:   50 GB    → r5.large (16 GB RAM, EBS-optimized)
  Graph working set:  200 GB    → r5.4xlarge (128 GB RAM, 8,000 baseline IOPS)
  Graph working set:  500 GB+   → r5.8xlarge (256 GB RAM, provisioned IOPS)
  Traversal-heavy:     any      → x2g instance (extended memory, SSD)

  Provisioned IOPS (io2 EBS): for high-concurrency multi-hop traversals
    IOPS budget = concurrent_traversals x avg_IO_per_traversal
    e.g., 100 concurrent 5-hop traversals x ~50 IO each = ~5000 IOPS minimum

Read replica scaling:
  Read replicas = ceil(max_concurrent_traversals / traversals_per_replica)
  Each replica serves its own copy of the graph (independent I/O pool)
  Auto-scaling target: EngineCPUUtilization 60% (scale-out threshold)

Neptune Streams filter patterns:
  Stream records contain: commitTimestamp, eventId, op, data
  Filter patterns:
    {"op": "ADD"}        → only insertions
    {"op": "REMOVE"}     → only deletions
    {"op": ["ADD","UPDATE"]} → insertions and updates
  Empty filter → all changes (highest volume)
```

**Key implication:** instance type determines both memory (graph working
set fit) and IOPS (traversal throughput). Read replica count scales
traversal concurrency horizontally. Stream filter patterns control
downstream processing volume — filter aggressively to reduce consumer
load.

## Recent features (2023-2025)

- **Neptune Analytics (2023-2024):** Serverless graph analytics for
  ad-hoc analysis without provisioning a cluster. Separate service from
  Neptune Database.
- **OpenCypher support (2023-2024):** Added OpenCypher query language
  support alongside Gremlin and SPARQL on the same cluster.
- **Improved bulk loader performance (2023-2024):** Higher throughput
  and better error handling for large graph loads.
- **Enhanced Streams (2024-2025):** Stream metrics in CloudWatch,
  improved filtering capabilities.
- **Global Database improvements (2024-2025):** Lower replication lag,
  more regions, faster failover.
- **Graviton-based instances (2024-2025):** r7g instance types for
  improved price/performance.
