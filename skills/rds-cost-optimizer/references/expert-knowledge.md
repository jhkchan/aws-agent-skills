# RDS Cost Optimizer — Expert Knowledge: Non-Obvious Cost Behaviours

These behaviours are easy to misjudge without database operational experience.
Each changes a recommendation if ignored.

## Multi-AZ cost mechanics

- **Multi-AZ doubles the compute cost but NOT the storage cost.** A Multi-AZ
  db.r6i.2xlarge costs 2 x $1.20/hour = $2.40/hour for compute. Storage is
  synchronously replicated to the standby but you only pay for the allocated
  storage once. Multi-AZ is a compute cost multiplier, not a storage multiplier.
- **Aurora does NOT charge extra for Multi-AZ.** Aurora replicates 6 copies
  of your data across 3 AZs by default — built into the Aurora storage cost
  ($0.10/GB-month vs RDS gp3 $0.08/GB-month). Aurora compute instances
  (writer + readers) are billed individually, but there is no "Multi-AZ
  surcharge" like RDS.
- **Disabling Multi-AZ** halves the compute cost (removes the standby) and
  causes a brief restart during the modification.

## Storage class details

- **gp3 includes 3000 IOPS and 125 MB/s throughput free.** Additional IOPS
  cost $0.005/provisioned-IOPS-month; additional throughput costs
  $0.04/provisioned-MB/s-month. Many databases paying for io2 provisioned
  IOPS could run on gp3 with free baseline IOPS.
- **io2 Block Express** costs $0.125/GB-month PLUS
  $0.10/provisioned-IOPS-month. A database with 10,000 provisioned IOPS pays
  $1,000/month in IOPS charges alone. Only databases with sustained high IOPS
  (and PI evidence of disk-bound queries) justify io2.
- **Storage autoscaling can silently inflate cost.** RDS auto-scales storage
  up to a configured maximum. You cannot shrink RDS storage — it only grows.
  Surface over-allocation as a finding.
- **RDS does not support in-place storage reduction.** There is no
  `modify-db-instance` to reduce AllocatedStorage.

## Pricing model nuances

- **Reserved Instances are Zonal or Regional.** A Zonal RI applies only to
  a Multi-AZ primary in that AZ. A Regional RI applies to any instance of
  that class in the region. For Multi-AZ databases, Regional RIs are
  recommended (the primary can fail over to any AZ).
- **RDS does NOT have a dedicated Savings Plan.** As of 2026, RDS only
  supports Reserved Instances. Compute Savings Plans apply to EC2, Fargate,
  and Lambda — NOT RDS. Always recommend RIs, never Savings Plans.
- **Manual snapshots bill indefinitely** at $0.095/GB-month until deleted.
  Automated snapshots auto-expire per backup retention period. Manual
  snapshots do NOT auto-expire.

## Aurora Serverless v2 specifics

- **Min ACU determines the floor cost.** Minimum ACU can be set as low as
  0.5 ($0.06/hour) but many users set it to 2-8 "for safety." At min ACU 8,
  the floor cost is $0.96/hour ($701/month) — the same as a fixed
  db.r6g.large. Serverless v2 only saves money when min ACU is set LOW.
- **Max ACU affects performance, not cost.** Cost is driven by ACTUAL ACU
  consumed. But a max ACU set too low throttles the database under load. Set
  max ACU to handle peak (2-4x baseline); set min ACU to baseline load.

## Engine and instance family

- **Graviton (Graviton2/3/4) RDS instances are ~20-30% cheaper** than x86
  equivalents. db.r6g.2xlarge costs ~$0.96/hour vs db.r6i.2xlarge at
  ~$1.20/hour. PostgreSQL and MySQL support Graviton. Oracle and SQL Server
  do NOT support Graviton.
- **License-included vs BYOL** for Oracle/SQL Server: License-included bundles
  the license into the hourly rate (~2-4x open-source). BYOL uses your
  existing license but requires Software Assurance and compliance tracking.

## Operational constraints

- **A stopped RDS instance still bills for storage.** Stopping eliminates
  compute charge but storage continues at $0.08-0.125/GB-month. After 7 days,
  AWS auto-starts the instance.
- **RDS does not support in-place instance-class changes without downtime.**
  Changing DBInstanceClass causes a brief outage (minutes). For Multi-AZ,
  failover-based modification minimises downtime but the database still
  briefly restarts. Schedule right-sizes during maintenance windows.
- **Snapshot restore is the rollback path** for instance-class changes.
  Before a right-size, take a manual snapshot: `aws rds create-db-snapshot`.
  RDS does not support in-place rollback of instance modifications.
