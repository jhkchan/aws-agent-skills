# Eval prompt: no-verification-split-brain

Validate this existing DR failover workflow. Emit the standard DR block.

Current state:
- Strategy: warm standby
- RTO target: 5 minutes, RPO target: 1 minute
- Primary: us-east-1, Secondary: us-west-2

Existing workflow:
- Route 53 health check: HTTPS /health, interval=30s, threshold=1
  (triggers on first failure)
- Lambda triggered directly by CloudWatch alarm on health check
  (no Step Functions orchestrator)
- Lambda immediately calls rds:promote-read-replica on the secondary
  (no prior verification that the primary is truly down)
- Lambda calls route53 change-resource-record-sets to update DNS
- No kill-switch
- No primary verification step (Lambda does not check if primary is
  still serving traffic before promoting)
- No post-failover verification (Lambda does not check if secondary is
  healthy before completing)
- No human approval gate (fully automatic)
- No game-day drill in 18 months
- Resilience Hub assessment score: 65 (below 80 target)
- CloudEndure running on 3 servers alongside DRS on others (conflict
  risk at block-replication layer)

Expected: MANUAL_STEP_REQUIRED. The skill must flag multiple CRITICAL
gaps:
1. No primary verification — a transient health check failure (network
   blip) triggers promotion while primary is still serving writes =
   split-brain, data divergence.
2. No kill-switch — a misconfigured health check endpoint causes
   endless failover flapping.
3. Health check threshold=1 — one transient failure triggers full
   failover. Use minimum threshold=3.
4. No drill in 18 months — configuration drift likely (stale AMIs,
   broken launch templates, IAM gaps).
5. No post-failover verification — clients may be routed to a broken
   secondary with no automatic rollback.
6. CloudEndure and DRS on same source servers — conflict at the
   block-replication layer.
