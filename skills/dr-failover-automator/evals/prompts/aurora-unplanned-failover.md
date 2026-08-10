# Eval prompt: aurora-unplanned-failover

Design an unplanned Aurora Global Database failover runbook for a
us-east-1 region outage. Emit the standard DR block.

Requirements:
- Application tier: DB + app
- RTO target: 15 minutes
- RPO target: 1 second (Aurora Global async replication lag)
- Primary region: us-east-1 (currently DOWN — full region outage)
- Secondary region: us-west-2 (to be promoted to standalone primary)
- Strategy: warm standby with Aurora Global Database

Failover procedure:
1. Verify primary region is down (Lambda dr-verify-primary-down with
   3 retries, 30s interval, 1.5x backoff — distinguishes transient
   failure from region outage)
2. rds remove-from-global-cluster on the us-west-2 secondary cluster
   (promotes it to standalone writable cluster)
3. Update Route 53 to point at the us-west-2 Aurora writer endpoint
4. Verify application writes succeed from us-west-2 (Lambda
   dr-verify-secondary-up)
5. Notify on-call via SNS (dr-notifications topic)
6. Human approval via SQS task token (no fixed Wait)

Rollback path documented:
- Once us-east-1 recovers, snapshot the new primary (us-west-2)
- Create a new global cluster with the snapshot as primary
- Add a new secondary in us-east-1
- The old primary cannot rejoin as secondary (promotion breaks
  replication permanently)

Orchestration: Step Functions state machine with kill-switch
(Parameter Store /dr/kill-switch), all steps above, SQS task-token
approval.

Game-day drill: 2026-07-10, unplanned failover tested end-to-end,
RTO measured 12min, RPO < 1s.

Expected: AUTOMATED. The unplanned failover runbook covers the
remove-from-global-cluster + promote sequence, DNS update, verification,
human approval, and a documented rollback path (snapshot + rebuild
global cluster). The game-day drill validates the RTO/RPO.
