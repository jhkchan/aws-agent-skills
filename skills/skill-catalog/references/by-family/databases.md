# Databases skills (31)

Precise call: `@skills:gh:jhkchan/aws-agent-skills/skills/<name>` (swap `<name>` for a row below).

| Skill | Task type | What it does |
|---|---|---|
| `aurora-cost-optimizer` | optimize | Optimises Amazon Aurora cluster cost across seven dimensions — instance-class right-sizing for Aurora Standard (db.r6/r7 vs db.t3/t4 burstable), Auror |
| `aurora-failover-operator` | operate | Operates Aurora cluster failover and recovery workflows safely — automatic Multi-AZ failover (30s detection, 60s promotion), planned failover to promo |
| `documentdb-cluster-deployer` | deploy | Provisions Amazon DocumentDB (MongoDB compatibility) clusters with production defaults: cluster creation (create-db-cluster), instance types (r5.large |
| `dynamodb-autoscaling-deployer` | deploy | Provisions DynamoDB auto-scaling with production defaults: target tracking for table (read/write capacity), target tracking for GSI (read/write capaci |
| `dynamodb-backup-operator` | operate | Operates DynamoDB backup and restore workflows safely — on-demand backups via create-backup, point-in-time recovery (PITR) enable/verify via update-co |
| `dynamodb-capacity-optimizer` | optimize | Optimises DynamoDB table cost across seven dimensions: on-demand vs provisioned capacity mode crossover analysis (30% utilization break-even), RCU/WCU |
| `dynamodb-global-tables-operator` | operate | Operates DynamoDB Global Tables safely across the full lifecycle: creating replicated tables in multiple regions, managing replication configuration,  |
| `dynamodb-table-auditor` | audit | Audits DynamoDB table configurations for encryption-at-rest (KMS), point-in- time recovery (PITR), capacity mode (on-demand vs provisioned with autosc |
| `dynamodb-table-deployer` | deploy | Provisions DynamoDB tables with production-grade defaults: partition key design (random suffix, composite keys), sort key design (range queries, hiera |
| `dynamodb-throttling-optimizer` | optimize | Optimises DynamoDB throttling prevention across eight dimensions: partition key design (hot partition detection via CloudWatch ThrottledRequests), bur |
| `dynamodb-throttling-troubleshooter` | troubleshoot | Diagnoses DynamoDB ProvisionedThroughputExceededException and throttle events via a symptom-to-cause decision tree covering read throttling, write thr |
| `elasticache-cache-deployer` | deploy | Provisions ElastiCache (Redis OSS / Memcached) clusters with production defaults: engine selection (Redis for persistence, clustering, pub/sub, TLS vs |
| `elasticache-cluster-deployer` | deploy | Provisions Amazon ElastiCache clusters with production defaults: Redis OSS self-designed clusters vs cluster mode enabled (shards and replicas), Memca |
| `elasticache-cost-optimizer` | optimize | Optimises Amazon ElastiCache cost across seven dimensions — node-type right-sizing (CloudWatch EngineCPUUtilization, CPUUtilization, CurrConnections), |
| `keyspaces-keyspace-deployer` | deploy | Provisions Amazon Keyspaces (Cassandra-compatible) keyspaces and tables with production defaults: keyspace creation (create-keyspace), table creation  |
| `memorydb-cluster-deployer` | deploy | Provisions Amazon MemoryDB for Redis clusters with production defaults: cluster creation (node type, shard count, replica count), subnets (subnet grou |
| `neptune-db-cluster-deployer` | deploy | Provisions Amazon Neptune DB clusters (graph database) with production defaults: cluster creation (instance type, cluster size, reader replicas), VPC  |
| `neptune-graph-deployer` | deploy | Provisions Amazon Neptune graph database clusters with production defaults: cluster creation (primary + read replicas), instance types, Neptune ML int |
| `qldb-ledger-deployer` | deploy | Provisions Amazon QLDB (Quantum Ledger Database) ledgers with production defaults: ledger creation (create-ledger), permissions mode (STANDARD vs ALLO |
| `rds-backup-restore-operator` | operate | Operates RDS and Aurora backup and restore workflows safely — automated backup window configuration, manual snapshots for pre-maintenance safety, cros |
| `rds-bluegreen-deployer` | deploy | Deploys Amazon RDS Blue/Green Deployments with production defaults: blue/green creation (create-blue-green-deployment — source to staging clone), swit |
| `rds-connectivity-troubleshooter` | troubleshoot | Diagnoses RDS and Aurora connection failures through a bidirectional- SG-first decision tree covering security group misconfiguration (wrong SG attach |
| `rds-cost-optimizer` | optimize | Optimises RDS and Aurora database cost through instance-class right-sizing (CloudWatch CPUUtilization, FreeableMemory, DatabaseConnections plus Perfor |
| `rds-failover-troubleshooter` | troubleshoot | Diagnoses RDS and Aurora failover issues through a thirteen-category diagnostic tree: Multi-AZ failover not triggering (health check threshold too con |
| `rds-instance-auditor` | audit | Audits AWS RDS DB instances for the seven high-impact configuration risks that drive data-loss and outage incidents — public accessibility (internet-e |
| `rds-instance-deployer` | deploy | Provisions RDS and Aurora databases with production-grade defaults: instance class selection (burstable t-series vs memory-optimized r-series vs gener |
| `rds-parameter-group-deployer` | deploy | Provisions RDS DB parameter groups with correct production defaults: family selection (postgres15, mysql8.0, aurora-postgresql15), static vs dynamic p |
| `rds-proxy-deployer` | deploy | Provisions Amazon RDS Proxy connections with production defaults: connection pooling (create-db-proxy), target Aurora cluster or serverless v2, Secret |
| `rds-snapshot-operator` | operate | Operates Amazon RDS and Aurora snapshot workflows end-to-end — automated backup retention (1-35 days) and the PITR window, manual snapshot creation (p |
| `rds-upgrade-operator` | operate | Operates Amazon RDS and Aurora engine upgrade workflows end-to-end — major version upgrades (explicit opt-in, pre-check: snapshot, parameter group com |
| `timestream-database-deployer` | deploy | Provisions Amazon Timestream databases and tables with production defaults: database creation (create-database), table creation (create-table) with re |
