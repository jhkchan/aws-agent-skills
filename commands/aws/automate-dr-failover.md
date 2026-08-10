---
description: Design and implement automated AWS disaster recovery failover. Cover the four DR strategies (backup & restore, pilot light, warm standby, multi-site active/active), Route 53 health-checked failover records, Aurora Global Database planned + unplanned failover, RDS cross-region read replica promotion, Elastic Disaster Recovery (DRS) launch with non-blocking agent, AWS Backup cross-region restore, S3 cross-region replication failover, Global Accelerator cross-region, Lambda multi-region deployment, Step Functions orchestration of the canonical failover sequence (health check, verify, promote, DNS, verify, notify), and AWS Resilience Hub readiness assessment. Enforces kill-switch, primary verification (split-brain prevention), game-day drill, and rollback path documentation.
nl_triggers:
  - "DR failover automation"
  - "Route 53 health-checked failover"
  - "Aurora Global Database failover"
  - "RDS cross-region read replica promotion"
  - "Elastic Disaster Recovery launch"
  - "pilot light DR strategy"
  - "warm standby DR"
  - "multi-site active active"
  - "AWS Backup cross-region restore"
  - "Lambda multi-region deploy"
  - "Step Functions failover orchestrator"
  - "Resilience Hub readiness assessment"
  - "RTO RPO analysis"
  - "S3 cross-region replication failover"
  - "Global Accelerator failover"
  - "DR game-day drill"
  - "kill-switch for failover"
routes_to: dr-failover-automator
---

# /aws:automate-dr-failover

Activate the `dr-failover-automator` skill and produce a DR failover
runbook design (or validation report).

## What it does

Reads an application tier, RTO/RPO targets, primary + secondary regions,
and either:

1. **Designs** a complete failover runbook with: DR strategy selection
   (backup-restore, pilot-light, warm-standby, multi-site based on
   RTO/RPO), Route 53 health-checked failover records, Aurora Global
   Database managed planned or unplanned failover, RDS cross-region read
   replica promotion, Elastic DRS recovery instance launch, AWS Backup
   cross-region restore, S3 CRR failover, Global Accelerator cross-region,
   Lambda multi-region deployment, and a Step Functions orchestrator
   executing the canonical failover sequence (kill-switch check -> verify
   primary down -> promote secondary -> update DNS -> verify secondary up
   -> notify -> human approval via SQS task token).
2. **Validates** an existing failover workflow against the mandatory
   safety baseline (kill-switch required, primary verification before
   promotion, post-failover verification, game-day drill within 90 days,
   health check threshold >= 3, rollback path documented, no CloudEndure
   + DRS conflict on same source).

Emits a deterministic block per design:

```text
STRATEGY: <backup-restore | pilot-light | warm-standby | multi-site>
RTO_TARGET: <minutes>
RPO_TARGET: <minutes>
REGIONS: primary=<region>, secondary=<region>
FAILOVER:
  - [PASS|FAIL] Route 53 health check configured (interval, threshold)
  - [PASS|FAIL] Primary verification step (prevent split-brain)
  - [PASS|FAIL] Secondary promotion mechanism defined
  - [PASS|FAIL] DNS update step
  - [PASS|FAIL] Verification step post-failover
  - [PASS|FAIL] Rollback path documented
ORCHESTRATION:
  - [PASS|FAIL] Step Functions state machine (or equivalent)
  - [PASS|FAIL] Kill-switch implemented
  - [PASS|FAIL] Human approval gate (task-token or manual)
VERIFICATION:
  - [PASS|FAIL] Game-day drill run within last 90 days
  - [PASS|FAIL] Resilience Hub assessment score >= target
  - [PASS|FAIL] Health check threshold tuned (not too sensitive)
VERDICT: AUTOMATED | MANUAL_STEP_REQUIRED
FINDINGS:
  - [INFO|WARN|HIGH|CRITICAL] <observation>
REMEDIATION:
  <numbered steps for fixing any FAIL findings>
```

## When to invoke

Provide RTO/RPO targets + regions and ask any of:

- "design pilot-light DR for a 3-tier app, RTO 30min, RPO 5min"
- "automate Aurora Global Database failover with Step Functions"
- "set up Route 53 health-checked failover for our ALB"
- "build a warm-standby DR with Global Accelerator"
- "validate our existing DR failover workflow for gaps"
- "design an Elastic DRS recovery plan for 20 EC2 instances"
- "run a Resilience Hub readiness assessment"

A bare RTO/RPO + regions + "DR" routes here via the orchestrator.

## Inputs

- **Required:** application_tier (web | app | db | mixed),
  rto_target_minutes (integer), rpo_target_minutes (integer),
  primary_region, secondary_region.
- **Recommended:** compliance_framework (PCI | HIPAA | FedRAMP),
  strategy_preference (backup-restore | pilot-light | warm-standby |
  multi-site), database_type (aurora-global | rds-replica | dynamodb-
  global-tables | none).
- **For validation mode:** existing failover workflow (Route 53 config
  JSON, Step Functions ASL JSON, Lambda function logic, health check
  config).

## Outputs

- One VERDICT block per design (AUTOMATED or MANUAL_STEP_REQUIRED).
- The complete failover runbook (strategy, building blocks, Step
  Functions ASL, Route 53 records, promotion commands) in
  STRATEGY/FAILOVER/ORCHESTRATION/VERIFICATION.
- Gate pass/fail per dimension in FAILOVER/ORCHESTRATION/VERIFICATION.
- Specific remediation steps for any failing gate in REMEDIATION.

## Related

- `/aws:pipeline` to enter the full CloudOps pipeline (this skill is the
  Phase 4 Automate specialist for disaster recovery).
- `/aws:operate-aurora-failover` for executing an Aurora failover
  (this skill designs the automation; operate executes it).
- `/aws:operate-route53-failover` for Route 53 failover record management.
- `/aws:audit-resiliencehub-app-assessment` for Resilience Hub posture
  (a verification input for this skill's runbooks).
- `/aws:operate-rds-backup-restore` for backup and restore operations.
- `/aws:automate-iac-template` to generate the CloudFormation template
  that deploys the failover orchestrator resources.
