# Example usage: dr-failover-automator

A walkthrough showing the skill designing a pilot-light DR failover plan
with Aurora Global Database, Route 53 health-checked failover, and Step
Functions orchestration. The skill emits an AUTOMATED verdict.

## Input (user prompt)

> Design a DR failover plan for our three-tier web application. We need
> RTO 30 minutes, RPO 5 minutes, us-east-1 to us-west-2. Use Aurora
> Global Database, pilot-light strategy with EC2 ASG scale-out, Route 53
> health-checked failover, and a Step Functions orchestrator with kill-
> switch and human approval.

## Skill output

```text
STRATEGY: pilot-light
RTO_TARGET: 30
RPO_TARGET: 5
REGIONS: primary=us-east-1, secondary=us-west-2
FAILOVER:
  - [PASS] Route 53 health check: HTTPS /health, interval=30s, threshold=3
  - [PASS] Primary verification: Lambda dr-verify-primary-down (3 retries, backoff)
  - [PASS] Aurora Global Database managed failover (failover-global-cluster)
  - [PASS] DNS update: Route 53 failover record UPSERT to secondary ALB
  - [PASS] Post-failover verification: Lambda dr-verify-secondary-up
  - [PASS] Rollback path documented (reverse DNS, failback via snapshot rebuild)
ORCHESTRATION:
  - [PASS] Step Functions state machine dr-failover-orchestrator
  - [PASS] Kill-switch: Parameter Store /dr/kill-switch (checked first)
  - [PASS] Human approval via SQS task token (no fixed Wait)
VERIFICATION:
  - [PASS] Game-day drill: 2026-07-15, RTO measured 22min, RPO 1s
  - [PASS] Resilience Hub assessment: compliance score 92
  - [PASS] Health check threshold tuned (3 failures, 30s = 90s detection)
VERDICT: AUTOMATED
FINDINGS:
  - [INFO] Aurora Global replication lag: 1s typical, 5s max observed
  - [INFO] DNS TTL 60s — clients may see 1-2min effective failover
  - [WARN] Application session state in ElastiCache — secondary has replica, verify failover works
  - [WARN] DRS source servers: 4 of 5 in sync, 1 lagging (re-sync scheduled)
REMEDIATION:
  1. Re-sync lagging DRS source server i-0primary5
  2. Add ElastiCache multi-AZ + cross-region replication for session state
```

## What the skill caught that a generic assistant misses

1. **Primary verification before promotion.** A generic assistant may
   promote the secondary on the first health check failure. The skill
   requires a verify-primary-down Lambda with retries — a transient
   network blip does not trigger a split-brain failover.

2. **Kill-switch checked FIRST.** A generic assistant may bury the
   kill-switch inside a Lambda. The skill puts it as the first Step
   Functions state — a misconfigured health check endpoint can be
   stopped with one parameter change.

3. **Post-failover verification with rollback.** A generic assistant
   may update DNS and call it done. The skill verifies the secondary is
   actually serving traffic post-DNS-update — if verification fails,
   the state machine automatically rolls back DNS to the primary.

4. **Task token for human approval (not Wait).** A generic assistant
   may use a fixed `Wait` state (e.g., "wait 1 hour for human"). The
   skill uses `waitForTaskToken` via SQS — the workflow pauses cleanly
   and resumes on callback, no dashboard clutter.

5. **Aurora Global unplanned failover loses ~1s of writes.** A generic
   assistant may claim zero data loss. The skill documents the
   worst-case RPO as the observed max replication lag, not the average.

6. **Game-day drill is mandatory.** A generic assistant may say "test
   regularly." The skill requires a drill within the last 90 days and
   cites the measured RTO — an untested failover plan is documentation,
   not DR.

## Slash-command invocation

```
/aws:automate-dr-failover
```

Or via the orchestrator:

```
/aws:pipeline
You: "design pilot-light DR for a 3-tier app, RTO 30min, RPO 5min, us-east-1 -> us-west-2"
```

## Live-account follow-up (optional, requires AWS CLI)

After deploying the failover orchestrator, validate the posture:

```bash
# Verify Route 53 health check exists and is healthy
aws route53 get-health-check \
  --health-check-id <hc-id> --profile default

# Verify Aurora Global cluster
aws rds describe-global-clusters \
  --query 'GlobalClusters[*].GlobalClusterIdentifier' --profile default

# Verify the Step Functions state machine exists
aws stepfunctions describe-state-machine \
  --state-machine-arn arn:aws:states:us-east-1:111111111111:stateMachine:dr-failover-orchestrator \
  --query 'status' --profile default

# Verify the kill-switch parameter
aws ssm get-parameter --name /dr/kill-switch --profile default

# Run a drill (DRS drill mode)
aws drs start-recovery \
  --source-servers i-0primary1 \
  --is-drill true \
  --profile default

# Verify Resilience Hub assessment
aws resiliencehub list-app-assessments \
  --app-arn arn:aws:resiliencehub:us-east-1:111111111111:app/123 \
  --query 'Assessments[0].AssessmentStatus' --profile default
```
