# Advanced Patterns (load on demand) — DR Failover Automator

Expert heuristic callouts, the edge-case catalog, and 2024-2026 AWS feature changes, moved verbatim from SKILL.md.


---

## Expert heuristic callouts (moved from SKILL.md)


- **Aurora Global unplanned failover loses ~1s of writes.** Storage-level
  async replication has typical lag under 1s but can spike. Document
  worst-case RPO as the observed max lag, not the average.
- **RDS MySQL cross-region replica replication uses binlog.** Big
  transactions can stall replication for minutes. Monitor with
  `aws rds describe-db-instances --query 'DBInstances[0].StatusInfos'`.
- **Route 53 health checks evaluate from multiple AWS regions globally.**
  A health check is healthy only if the endpoint responds from all
  health-check regions. A regionally-restricted endpoint may fail health
  checks from other regions.
- **Step Functions Route 53 integration is synchronous.**
  `arn:aws:states:::route53:changeResourceRecordSets` waits for the
  change to reach INSYNC (typically within 60 seconds).
- **Elastic DRS recovery instances use the staging area's latest sync
  point.** No PITR concept — recovery is always at the latest replicated
  state. For PITR, layer in AWS Backup.
- **Global Accelerator anycast IPs survive regional outages.** Clients
  connecting via anycast IPs route to the nearest healthy region
  automatically. Sub-second failover without DNS update.
- **Aurora Serverless v2 secondaries are cost-effective for warm standby.**
  Scale to minimum (0.5 ACU) when idle; scales up when promoted.
- **AWS Backup restore time scales with snapshot size.** A 10TB EBS
  snapshot restore can take hours. Use incremental snapshots for large
  volumes.
- **DynamoDB Global Tables support multi-region active-active writes.**
  Last-writer-wins is the default — design for idempotency.
- **CloudEndure is being sunset; migrate to Elastic DRS.** Do not run
  both simultaneously on the same source server — they conflict at the
  block-replication layer.

## Edge-case handling (moved from SKILL.md)


- **Split-brain during failover.** If primary verification fails (Lambda
  error) but the orchestrator proceeds, two primaries serve writes.
  The state machine MUST gate promotion behind a successful verification
  state — abort on verification failure.
- **DNS cache extends effective RTO.** Even with 60s TTL, mobile
  carriers and OS-level caches can hold the old endpoint for 5+ minutes.
  For tier-0 apps, use Global Accelerator (anycast IPs change without
  DNS update).
- **Replication lag exceeds RPO.** Aurora Global or RDS replica falls
  behind. Monitor lag continuously; alert if lag approaches RPO target.
- **DR region outage.** For tier-0, consider a tertiary region or
  active/active across three regions.
- **CloudEndure to DRS migration.** AWS provides a migration script —
  plan 2-4 weeks per project. Do not run both on the same source.
- **Health check endpoint behind authentication.** Route 53 health
  checks do not perform auth — expose an unauthenticated `/health`
  endpoint.

## Recent AWS features (2024-2026) (moved from SKILL.md)


- **Aurora Global Database Managed Planned Failover (2024-2025):**
  One-API-call planned failover with no data loss. For drills and
  controlled failover.
- **Elastic Disaster Recovery non-blocking agent (2024-2025):** Decouples
  replication from source-server I/O. No performance impact under heavy
  write load.
- **AWS Resilience Hub drift detection (2024-2025):** Periodic
  re-assessment detects configuration drift. Schedule monthly via
  EventBridge.
- **Route 53 health check improvements (2024-2025):** Custom headers and
  request body support for health endpoints requiring API key.
- **AWS Backup logical-tier support (2024-2025):** SAP HANA, VMware Cloud
  on AWS, FSx for NetApp ONTAP — broader DR coverage.
- **DynamoDB Global Tables (2024-2025):** Custom Lambda-based merge
  beyond last-writer-wins for multi-writer workloads.
- **Global Accelerator custom routing (2024-2025):** Non-HTTP workloads
  (TCP/UDP) for multi-region gaming or VOIP backends.
- **S3 CRR with Replication Time Control (2024-2025):** 15-minute SLA
  on object replication — tighter S3 RPO.
- **Step Functions Distributed Map (2024-2025):** Iterate over many
  resources (1000+ EC2 instances) for large-scale DR orchestration.