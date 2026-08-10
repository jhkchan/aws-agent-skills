# RDS Cost Optimizer — Read Replica and Multi-AZ Constraints

These constraints affect right-sizing recommendations when the database
topology includes read replicas or Multi-AZ standby instances. Failing to
account for these produces recommendations that break replication or
underestimate cost impact.

## Read replicas — downsize primary breaks replicas

**Problem:** RDS read replicas should run the same instance class as (or
larger than) the primary for replication stability. Downsizing the primary
WITHOUT first downsizing the replicas can cause replication lag or errors.
Downsizing the primary below the largest replica's class is not supported
and will be rejected by the RDS API.

**Detection:**
```bash
aws rds describe-db-instances --output json | \
  jq '.DBInstances[] | select(.ReadReplicaSourceDBInstanceIdentifier == "<primary-id>")
  | {DBInstanceIdentifier, DBInstanceClass, Status}'
```

**Resolution path:**
1. Identify all read replicas of the primary.
2. Downsize replicas FIRST, then the primary.
3. Each replica downsize requires its own modification and brief downtime.
4. After each replica downsize, verify `ReplicaLag` < 5 seconds before
   proceeding to the next.
5. For Aurora: read replicas are Aurora Replicas within the cluster.
   Downsizing the Aurora writer does NOT automatically downsize readers —
   each reader instance must be modified separately.
6. If any replica serves a latency-sensitive read workload, verify it can
   handle the smaller instance class independently.

**Example migration sequence:**
```
Primary: db.r5.2xlarge (Multi-AZ, $1,499/month compute)
Replica 1: db.r5.2xlarge (Single-AZ, $750/month compute)
Replica 2: db.r5.2xlarge (Single-AZ, $750/month compute)

Downsize sequence (all to db.r5.large):
  1. Modify Replica 1 to db.r5.large, verify ReplicaLag < 5s for 24h
  2. Modify Replica 2 to db.r5.large, verify ReplicaLag < 5s for 24h
  3. Modify Primary to db.r5.large (Multi-AZ failover, ~5 min downtime)
  4. Verify replication health for 7 days
  5. Purchase RIs for all three instances at the new class
```

When read replicas exist, MIGRATION_STEPS must include per-replica
modifications and verification gates. The total saving includes ALL instances
(primary + all replicas), not just the primary.

## Multi-AZ — both instances change simultaneously

**Problem:** Modifying a Multi-AZ RDS instance class updates the standby
first, fails over to it, then updates the old primary. Three implications:

1. The cost change applies to BOTH instances (primary + standby).
2. There is a brief failover during the modification (30s to 3min disruption).
3. The RI coverage must account for BOTH instances.

**Detection:**
```bash
aws rds describe-db-instances --db-instance-identifier <id> --output json | \
  jq '.DBInstances[0] | {MultiAZ, DBInstanceClass, DBSubnetGroup}'
```

**Resolution path:**

1. **Cost impact is doubled.** A Multi-AZ downsize saves on BOTH the primary
   and standby. Compute savings as `2 x (old_hourly - new_hourly) x 730`.

2. **RI sizing for Multi-AZ.** Use
   `aws rds describe-reserved-db-instances-offerings --multi-az` to find
   Multi-AZ RI offerings covering both instances. Alternatively, purchase
   two standard Regional RIs.

3. **Downtime planning.** Failover causes 30s-3min connection drop.
   Applications with retry logic recover automatically. Schedule during
   maintenance window. Warn in the CONFIRM gate.

4. **Aurora exception.** Aurora does NOT charge extra for Multi-AZ (6 copies
   across 3 AZs included in storage cost). This constraint applies to RDS
   for PostgreSQL/MySQL/Oracle/SQL Server, not Aurora.

**Example cost computation:**
```
Multi-AZ db.r5.2xlarge On-Demand:
  Primary:  db.r5.2xlarge at $1.027/hr x 730 = $749.71/month
  Standby:  db.r5.2xlarge at $1.027/hr x 730 = $749.71/month
  Total compute: $1,499.42/month

After downsize to db.r5.large Multi-AZ + 1yr RI:
  Primary:  db.r5.large at $0.548/hr x 730 x 0.60 = $240.02/month
  Standby:  db.r5.large at $0.548/hr x 730 x 0.60 = $240.02/month
  Total compute: $480.05/month

Saving: $1,019.37/month (68.0%)
RI action: purchase Multi-AZ RI for db.r5.large to cover both instances.
```
