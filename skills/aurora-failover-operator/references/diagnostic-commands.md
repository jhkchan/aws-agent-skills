# Aurora Failover Operator — Diagnostic & Pre-flight Commands

Diagnostic and pre-flight command listings moved from SKILL.md.
Load on demand when executing against a live account.


## Live-account pre-flight (moved from SKILL.md § Pre-flight)

**Live-account pre-flight (skip if offline plan audit):**
1. `aws rds describe-db-clusters --db-cluster-identifier <id>` — confirm
   `DBClusterStatus: available`. Capture `Engine`, `EngineVersion`,
   `MultiAZ`, `DBClusterMembers` (writer/reader roles, `IsClusterWriter`
   flag), `GlobalClusterIdentifier` (if Global DB member), `DBSubnetGroup`,
   `VpcSecurityGroups`, `DBClusterEndpoint` (writer and reader endpoints),
   `AllocatedStorage`, `StorageEncrypted`, `KmsKeyId`.
2. `aws rds describe-db-instances --db-cluster-identifier <id>` — capture
   per-instance status, AZ, instance class, `AuroraReplicaLag`,
   `DBInstanceStatus`.
3. `aws rds describe-global-clusters --global-cluster-identifier <gid>`
   (if Global DB member) — capture global cluster membership, primary
   region, secondary regions.
4. `aws rds describe-db-proxy-target-groups --target-group-name <tg>` (if
   RDS Proxy is associated) — verify target health.
5. `aws ec2 describe-subnets --filters Name=vpc-id,Values=<vpc-id>` —
   verify the cluster's subnets span multiple AZs.
