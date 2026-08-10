---
name: dr-failover-automator
description: >-
  Designs AWS disaster recovery failover automation across the four DR
  strategies (backup & restore, pilot light, warm standby, multi-site
  active/active), Route 53 health-checked failover records, Aurora
  Global Database planned + unplanned failover, S3 cross-region
  replication failover, RDS cross-region read replica promotion,
  Elastic Disaster Recovery (DRS) launch, AWS Backup cross-region
  restore, cross-zone + cross-region load balancing (Global
  Accelerator), Lambda multi-region, and Step Functions orchestration
  of the canonical failover sequence (health check, promote, DNS,
  verify, notify). Includes AWS Resilience Hub readiness assessment
  and Elastic DRS non-blocking agent. Emits AUTOMATED with failover
  runbook or MANUAL_STEP_REQUIRED with the gap. Use when designing DR
  failover, RTO/RPO analysis, or resilience assessment.
version: 0.1.0
author: Jacky Chan — AWS Community Builder
license: Apache-2.0
compatibility: >-
  Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex,
  Gemini). No AWS CLI required for offline plan authoring. Live deployment
  uses aws route53 change-resource-record-sets (failover record, health check),
  aws rds failover-global-cluster (Aurora Global), promote-read-replica
  (RDS cross-region), aws drs start-recovery (Elastic DRS),
  aws backup start-restore-job (cross-region restore),
  aws elasticloadbalancing modify-load-balancer-attributes (cross-zone),
  aws lambda create-function / update-function-code (multi-region deploy),
  aws stepfunctions start-execution (orchestration),
  aws resiliencehub create-app + start-app-assessment — AWS CLI v2,
  SSO or key-based, primary + secondary region credentials.
keywords:
  - disaster recovery
  - DR failover
  - backup and restore
  - pilot light
  - warm standby
  - multi-site active-active
  - Route 53 health check
  - Route 53 failover record
  - Aurora Global Database
  - cross-region read replica
  - Elastic Disaster Recovery
  - DRS launch
  - CloudEndure migration
  - AWS Backup cross-region restore
  - cross-zone load balancing
  - Global Accelerator
  - Lambda multi-region
  - Step Functions failover orchestration
  - AWS Resilience Hub
  - RTO RPO
  - S3 cross-region replication
tags:
  - disaster-recovery
  - route53
  - aurora-global
  - elastic-drs
  - aws-backup
  - resilience-hub
  - stepfunctions
  - automate
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: true
  phase: 4
  supports_pipeline: true
  entry_point: false
  family: Management
  task_type: automate
  skill_class: capability
  lifecycle_status: active
  verdict_shape: AUTOMATED | MANUAL_STEP_REQUIRED
  when_to_use: >-
    Designing a DR failover plan, picking among backup-restore / pilot
    light / warm standby / multi-site strategies, wiring Route 53
    health-checked DNS failover, automating Aurora Global Database or
    RDS cross-region replica promotion, orchestrating Elastic Disaster
    Recovery (DRS) launch, centralizing AWS Backup cross-region restore,
    deploying Lambda multi-region with Route 53 failover, building a
    Step Functions failover orchestrator (health check -> promote ->
    DNS -> verify -> notify), or running an AWS Resilience Hub readiness
    assessment.
  when_not_to_use:
    - Single-region high availability (use autoscaling / multi-AZ skills — DR is cross-region by definition).
    - Backup-only design with no failover component (use backup / data-protection skills).
    - Application-level health check design (use app-monitoring skills — this skill automates failover, not monitoring).
    - Migration planning (use migration skills — DR is about failover, not lift-and-shift).
  activation_triggers:
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
  invocation_schema: >-
    Input: either (a) a DR requirement ("design pilot-light DR for a
    three-tier app, RTO 30min, RPO 5min, us-east-1 -> us-west-2"),
    OR (b) an existing failover workflow / Route 53 configuration /
    Aurora Global cluster to audit and harden. Output: deterministic
    DR block per requirement — STRATEGY/FAILOVER/ORCHESTRATION/VERIFICATION/
    VERDICT — where VERDICT is AUTOMATED (failover runbook complete with
    all gates passing) or MANUAL_STEP_REQUIRED (specific gap cited,
    e.g., health check missing, untested RDS promotion, no break-glass
    notification path).
---

# DR Failover Automator

## What this skill does

Designs automated AWS disaster recovery failover across the four
canonical DR strategies — **backup & restore**, **pilot light**, **warm
standby**, and **multi-site active/active** — and the building blocks
that compose each: Route 53 health-checked DNS failover, Aurora Global
Database failover, RDS cross-region read replica promotion, Elastic
Disaster Recovery (DRS) launch, AWS Backup cross-region restore,
cross-zone / cross-region load balancing, Lambda multi-region deployment,
and Step Functions orchestration of the canonical failover sequence
(health check -> promote primary -> update DNS -> verify -> notify).

The verdict is binary: **AUTOMATED** when the runbook covers a chosen
strategy with mapped RTO/RPO targets, a defined trigger (health check
or manual), the full failover sequence, verification step, and rollback
path; **MANUAL_STEP_REQUIRED** when any component is missing (e.g.,
health check threshold undefined, untested promotion, no verification
hook, no break-glass notification).

## Quick navigation

| # | Section | Jump when |
|---|---|---|
| 1 | [Pre-flight gate](#pre-flight-dr-spec-gate) | Starting any DR design — blocks unsafe specs |
| 2 | [Decision tree](#decision-tree--strategy-selection) | Backup-restore / pilot light / warm standby / multi-site |
| 3 | [Route 53 failover](#route-53-health-checked-failover) | DNS-level failover with health checks |
| 4 | [Aurora Global Database](#aurora-global-database-failover) | Planned + unplanned cross-region DB failover |
| 5 | [RDS cross-region replica](#rds-cross-region-read-replica-promotion) | Cross-region read replica promotion |
| 6 | [Elastic Disaster Recovery](#elastic-disaster-recovery-drs) | DRS launch + recovery instance |
| 7 | [AWS Backup cross-region](#aws-backup-cross-region-restore) | Cross-region restore orchestration |
| 8 | [S3 cross-region replication](#s3-cross-region-replication-failover) | CRR + Route 53 client failover |
| 9 | [Load balancer failover](#load-balancer-cross-zone--cross-region) | ALB/NLB cross-zone, Global Accelerator |
| 10 | [Lambda multi-region](#lambda-multi-region-deployment) | SAM multi-region + Route 53 failover |
| 11 | [Step Functions orchestrator](#step-functions-failover-orchestration) | The canonical failover state machine |
| 12 | [Resilience Hub](#aws-resilience-hub-readiness-assessment) | DR readiness scoring + drift detection |
| 13 | [STRICT output contract](#output-format-strict-output-contract) | The exact DR block the skill emits |
| 14 | [NEVER anti-patterns](#never-these-things) | The hardcoded list of DR taboos |
| 15 | [Expert heuristic](#expert-heuristic-callouts) | Non-obvious behaviors that change the design |
| 16 | [Recent AWS features](#recent-aws-features-2024-2026) | Managed planned failover, non-blocking DRS, Resilience Hub |

## Mindset

**One-line takeaway:** disaster recovery is **RTO + RPO + tested failover**.
An untested failover plan is documentation, not DR. The first time you
promote a cross-region Aurora Global cluster should be in a game-day
exercise — not during a real outage when the database is down and
everyone is stressed.

- **The DR strategy is a cost/continuum trade-off, not a binary.**
  Backup-and-restore is cheapest but highest RTO/RPO. Multi-site
  active/active is most expensive but lowest RTO/RPO (near-zero). The
  right strategy meets the business RTO/RPO at the lowest cost.
- **Route 53 health checks fail in 10-60 seconds; DNS TTL adds to that.**
  A failover record with a 60s TTL + 30s health check interval gives
  ~90s DNS-level RTO. Client/resolver caching can push effective RTO
  to 5+ minutes.
- **Failover without verification is a footgun.** A health check that
  triggers a promotion before the primary is truly down causes a
  split-brain — two primaries accepting writes. Always verify the
  primary is unreachable before promoting the secondary.

## Pre-flight: DR spec gate (run before generation)

| Attribute | Required | Effect on plan |
|---|---|---|
| `application_tier` | YES | Determines building blocks (DB, compute, storage, DNS) |
| `rto_target_minutes` | YES | Determines strategy (backup, pilot, warm, multi-site) |
| `rpo_target_minutes` | YES | Determines replication mode (async, sync, snapshot interval) |
| `primary_region` | YES | Source region |
| `secondary_region` | YES | DR region |
| `compliance_framework` | Recommended | PCI/HIPAA/FedRAMP may mandate tested DR |
| `existing_failover` | For audit mode | When provided, run the layer gates |

**If the spec is incomplete**, output:

```text
STRATEGY: <unknown>
FAILOVER: <unknown>
ORCHESTRATION: <unknown>
VERIFICATION: <unknown>
VERDICT: MANUAL_STEP_REQUIRED
REASON: Spec is missing required fields (<list>).
REQUIRED:
  - application_tier (web | app | db | mixed)
  - rto_target_minutes (integer)
  - rpo_target_minutes (integer)
  - primary_region, secondary_region
REMEDIATION: Provide all required fields. Example: "design pilot-light
DR for a 3-tier app, RTO 30min, RPO 5min, us-east-1 -> us-west-2"
maps to application_tier=mixed, rto_target_minutes=30,
rpo_target_minutes=5.
```

**Live-account pre-flight checks (skip for offline authoring):**
1. Verify Route 53 hosted zone exists: `aws route53 list-hosted-zones`.
2. Verify secondary region enabled: `aws account get-region-opt-status --region-name <secondary>`.
3. Verify Aurora Global cluster (if applicable): `aws rds describe-global-clusters`.
4. Verify Elastic DRS source servers synced: `aws drs describe-source-servers`.
5. Verify AWS Backup vault in secondary region: `aws backup list-backup-vaults --region <secondary>`.

## Decision tree — strategy selection

```
START
  ├─ rto > 24h AND rpo > 24h? ─────────────► Backup & Restore
  ├─ rto 1-24h AND rpo 15min-1h? ──────────► Pilot Light
  ├─ rto 1-60min AND rpo < 15min? ─────────► Warm Standby
  ├─ rto < 1min AND rpo ~0? ───────────────► Multi-Site Active/Active
  └─ (insufficient objectives) ─────────────► MANUAL_STEP_REQUIRED
```

| Strategy | RTO | RPO | Cost | When to use |
|---|---|---|---|---|
| Backup & restore | Hours-days | Hours-days | 1x storage | Archives, dev, low-criticality |
| Pilot light | 10min-1h | Minutes | 1x replica | Tier 2-3 apps |
| Warm standby | Single-digit min | Seconds-min | 50-100% secondary | Tier 1 apps |
| Multi-site active/active | Near-zero | Near-zero | 200% duplicate | Tier 0 / revenue-critical |

**Component-to-building-block mapping:**

| Component | RPO target | Building block |
|---|---|---|
| Aurora DB | < 1s | Aurora Global Database (async, ~1s lag) |
| Aurora DB | 5min (PITR) | Aurora automated backup (5-min PITR) |
| RDS MySQL/PostgreSQL | < 1s | Cross-region read replica (async) |
| DynamoDB | Near-zero | DynamoDB Global Tables (multi-region active-active) |
| S3 data | < 15min | S3 cross-region replication (CRR) |
| EBS volumes | Hours | AWS Backup cross-region copy |
| EC2 stateful | Hours | Elastic DRS continuous replication |

## Route 53 health-checked failover

```bash
# Create health check on the primary
HC_ID=$(aws route53 create-health-check \
  --caller-reference "primary-hc-$(date +%s)" \
  --health-check-config '{
    "Type": "HTTPS",
    "FullyQualifiedDomainName": "primary.example.com",
    "Port": 443,
    "ResourcePath": "/health",
    "RequestInterval": 30,
    "FailureThreshold": 3
  }' --query 'HealthCheck.Id' --output text)

# Create failover routing policy
aws route53 change-resource-record-sets --hosted-zone-id <zone-id> \
  --change-batch '{
    "Changes": [
      {"Action":"CREATE","ResourceRecordSet":{
        "Name":"app.example.com","Type":"A",
        "SetIdentifier":"primary","Failover":"PRIMARY",
        "AliasTarget":{"HostedZoneId":"Z2FDTNDATAQYW2",
          "DNSName":"primary-alb.us-east-1.elb.amazonaws.com",
          "EvaluateTargetHealth":true},
        "HealthCheckId":"'"$HC_ID"'"}},
      {"Action":"CREATE","ResourceRecordSet":{
        "Name":"app.example.com","Type":"A",
        "SetIdentifier":"secondary","Failover":"SECONDARY",
        "AliasTarget":{"HostedZoneId":"Z2FDTNDATAQYW2",
          "DNSName":"secondary-alb.us-west-2.elb.amazonaws.com",
          "EvaluateTargetHealth":true}}}
    ]
  }'
```

**Routing policies:** Failover (primary->secondary on health check
failure), Weighted (split 90/10), Latency (route to lowest-latency
region), Geolocation (route by client geography).

**Gotchas:** TTL matters — a 60s TTL gives 60s client cache. Health
check `FailureThreshold` x `RequestInterval` = detection time (3 x 30s
= 90s). `EvaluateTargetHealth: true` cascades health to the ALB/NLB.

## Aurora Global Database failover

Aurora Global provides a primary cluster in one region + up to 5
secondary read-only clusters. Storage-level async replication (~1s lag).

### Managed planned failover (2024-2025)
```bash
aws rds failover-global-cluster \
  --global-cluster-identifier my-global-cluster \
  --target-db-cluster-identifier arn:aws:rds:us-west-2:111111111111:cluster:my-secondary
```
Promotes secondary in < 1 minute with no data loss. Use for DR drills
and controlled failover.

### Unplanned failover (outage)
```bash
# Detach + promote secondary (standalone writable cluster)
aws rds remove-from-global-cluster \
  --db-cluster-identifier arn:aws:rds:us-west-2:111111111111:cluster:my-secondary \
  --global-cluster-identifier my-global-cluster
# Update Route 53 to point at new primary; verify application writes
```
May lose the last ~1s of writes (replication lag). After unplanned
failover, the old primary cannot rejoin — rebuild the global cluster.

## RDS cross-region read replica promotion

For non-Aurora RDS (MySQL, PostgreSQL):

```bash
# One-time setup: create cross-region read replica
aws rds create-db-instance-read-replica \
  --db-instance-identifier my-db-replica \
  --source-db-instance-identifier arn:aws:rds:us-east-1:111111111111:db:my-db \
  --region us-west-2

# On failover: promote to standalone
aws rds promote-read-replica \
  --db-instance-identifier my-db-replica --region us-west-2
```

**Gotchas:** promotion breaks replication — the original primary cannot
re-add as a replica without re-snapshot. Cross-region async replication
has lag (seconds-minutes). Promotion takes 5-20 minutes (account for
this in RTO).

## Elastic Disaster Recovery (DRS)

DRS provides continuous block-level replication from source servers to a
staging area in the DR region. On failover, launches EC2 recovery
instances from the replicated data.

### Launch recovery instances
```bash
aws drs start-recovery \
  --source-servers i-0primary1,i-0primary2 \
  --is-drill false
```

### Non-blocking agent (2024-2025)
Decouples replication from application I/O — source-server performance is
not impacted under heavy write load. Older agents blocked I/O during
replication bursts.

### Drill mode
```bash
aws drs start-recovery --source-servers i-0primary1 --is-drill true
```
Launches recovery instances in an isolated subnet without affecting
production. Run quarterly drills.

**Gotchas:** DRS does NOT replicate IAM role, security group, or tags —
configure in launch templates. Recovery launch takes 5-30 min. Staging
area cost is continuous. CloudEndure is being sunset — migrate to DRS.

## AWS Backup cross-region restore

```bash
# Cross-region copy in backup plan
aws backup create-backup-plan --backup-plan '{
  "BackupPlanName":"cross-region-daily",
  "Rules":[{
    "RuleName":"DailyBackup",
    "TargetBackupVaultName":"Default",
    "ScheduleExpression":"cron(0 5 ? * * *)",
    "CopyActions":[{
      "DestinationBackupVaultArn":"arn:aws:backup:us-west-2:111111111111:backup-vault:Default",
      "Lifecycle":{"DeleteAfterDays":30}
    }]
  }]
}'

# Restore on failover
aws backup start-restore-job \
  --recovery-point-arn arn:aws:backup:us-west-2:111111111111:recovery-point:1-xxx \
  --metadata '{"InstanceType":"t3.large","VpcId":"vpc-xxx"}' \
  --iam-role-arn arn:aws:iam::111111111111:role/AWSBackupRestoreRole \
  --resource-type EC2
```

**Gotchas:** restore time scales with snapshot size (1TB EBS = 30-60min).
Cross-region copy happens after local backup completes. RPO = backup
interval + copy time.

## S3 cross-region replication failover

```bash
aws s3api put-bucket-replication --bucket primary-bucket \
  --replication-configuration '{
    "Role":"arn:aws:iam::111111111111:role/S3ReplicationRole",
    "Rules":[{"Status":"Enabled","Priority":1,
      "Destination":{"Bucket":"arn:aws:s3:::secondary-bucket"},
      "Filter":{}}]
  }'
```

**Failover pattern:** Route 53 failover records pointing at the two
buckets (via CloudFront), OR update application S3 client to the
secondary bucket ARN. S3 CRR is async — recent objects may not yet be
replicated at failover. Use S3 Batch Operations post-failover to
identify and re-upload missing objects.

## Load balancer cross-zone + cross-region

### Cross-zone (within region)
```bash
aws elbv2 modify-load-balancer-attributes \
  --load-balancer-arn <alb-arn> \
  --attributes Key=load_balancing.cross_zone.enabled,Value=true
```
ALB cross-zone is on by default. NLB cross-zone is off by default.

### Cross-region (Global Accelerator)
```bash
aws globalaccelerator create-accelerator --name dr-global-accelerator
# Primary endpoint group: traffic-dial-percentage 100
# Secondary endpoint group: traffic-dial-percentage 0
# Flip dials on failover
```
Global Accelerator provides static anycast IPs that route to the nearest
healthy regional endpoint. Sub-second failover — better than DNS TTL.

## Lambda multi-region deployment

```bash
sam package --template-file template.yaml \
  --s3-bucket sam-bucket-us-east-1 --output-template-file packaged.yaml
sam deploy --template-file packaged.yaml --stack-name my-fn --region us-east-1
sam deploy --template-file packaged.yaml --stack-name my-fn --region us-west-2
```
Front with Route 53 failover records pointing at regional API Gateway /
Function URL. **Gotcha:** Lambda env vars and IAM roles are
region-specific. Use Parameter Store cross-region replication or
Secrets Manager replica for shared config.

## Step Functions failover orchestration

The canonical failover sequence: health check -> promote primary ->
update DNS -> verify -> notify.

```json
{
  "StartAt": "CheckKillSwitch",
  "States": {
    "CheckKillSwitch": {
      "Type": "Task",
      "Resource": "arn:aws:states:::ssm:get-parameter",
      "Parameters": {"Name": "/dr/kill-switch"},
      "Next": "KillSwitchChoice"
    },
    "KillSwitchChoice": {
      "Type": "Choice",
      "Choices": [{"Variable": "$.Parameter.Value", "StringEquals": "disabled", "Next": "AbortFailover"}],
      "Default": "ConfirmPrimaryDown"
    },
    "AbortFailover": {"Type": "Succeed", "Comment": "Kill-switch tripped"},
    "ConfirmPrimaryDown": {
      "Comment": "Verify primary is truly down — prevent split-brain",
      "Type": "Task",
      "Resource": "arn:aws:lambda:<region>:<account>:function:dr-verify-primary-down",
      "Retry": [{"ErrorEquals": ["States.TaskFailed"], "IntervalSeconds": 30, "MaxAttempts": 3, "BackoffRate": 1.5}],
      "Next": "PrimaryDownChoice"
    },
    "PrimaryDownChoice": {
      "Type": "Choice",
      "Choices": [{"Variable": "$.primaryHealthy", "BooleanEquals": true, "Next": "AbortFailover"}],
      "Default": "PromoteSecondary"
    },
    "PromoteSecondary": {
      "Type": "Task",
      "Resource": "arn:aws:lambda:<region>:<account>:function:dr-promote-secondary",
      "Next": "UpdateDNS"
    },
    "UpdateDNS": {
      "Type": "Task",
      "Resource": "arn:aws:states:::route53:changeResourceRecordSets",
      "Parameters": {
        "HostedZoneId": "<zone-id>",
        "ChangeBatch": {"Changes": [{"Action": "UPSERT", "ResourceRecordSet": {
          "Name": "app.example.com", "Type": "A",
          "AliasTarget": {"HostedZoneId": "Z2FDTNDATAQYW2",
            "DNSName": "secondary-alb.us-west-2.elb.amazonaws.com",
            "EvaluateTargetHealth": true}
        }}]}
      },
      "Next": "VerifySecondaryUp"
    },
    "VerifySecondaryUp": {
      "Type": "Task",
      "Resource": "arn:aws:lambda:<region>:<account>:function:dr-verify-secondary-up",
      "Next": "VerifyChoice"
    },
    "VerifyChoice": {
      "Type": "Choice",
      "Choices": [{"Variable": "$.secondaryHealthy", "BooleanEquals": true, "Next": "NotifySuccess"}],
      "Default": "RollbackDNS"
    },
    "NotifySuccess": {
      "Type": "Task",
      "Resource": "arn:aws:sns:<region>:<account>:dr-notifications",
      "Next": "WaitForHumanApproval"
    },
    "RollbackDNS": {
      "Type": "Task",
      "Resource": "arn:aws:states:::route53:changeResourceRecordSets",
      "Parameters": {
        "HostedZoneId": "<zone-id>",
        "ChangeBatch": {"Changes": [{"Action": "UPSERT", "ResourceRecordSet": {
          "Name": "app.example.com", "Type": "A",
          "AliasTarget": {"HostedZoneId": "Z2FDTNDATAQYW2",
            "DNSName": "primary-alb.us-east-1.elb.amazonaws.com",
            "EvaluateTargetHealth": true}
        }}]}
      },
      "Next": "NotifyFailure"
    },
    "NotifyFailure": {"Type": "Task", "Resource": "arn:aws:sns:<region>:<account>:dr-critical-alerts", "End": true},
    "WaitForHumanApproval": {
      "Type": "Task",
      "Resource": "arn:aws:states:::sqs:sendMessage.waitForTaskToken",
      "Parameters": {"QueueUrl": "https://sqs.<region>.amazonaws.com/<account>/dr-approval",
        "MessageBody": {"failoverId.$": "$.failoverId", "taskToken.$": "$$.Task.Token"}},
      "End": true
    }
  }
}
```

Always prefer `waitForTaskToken` for human approval gates — pauses
cleanly, resumes on callback. Avoid `Wait` with fixed duration (clutters
dashboard, may hit 1-year execution limit).

## AWS Resilience Hub readiness assessment

```bash
aws resiliencehub create-app --app-name my-dr-app \
  --resource-mappings '[{"PhysicalResourceId":"arn:aws:rds:us-east-1:111111111111:cluster:my-db","LogicalResourceId":{"Identifier":"my-db"},"MappingType":"CfnStack"}]'

aws resiliencehub start-app-assessment \
  --app-arn arn:aws:resiliencehub:<region>:<account>:app/123 \
  --app-version-name release-1 --assessment-name dr-readiness-2026-08
```

Returns a compliance score + recommendations ("add Aurora Global for
RPO < 1s compliance"). Use as the readiness gate for go-live. Requires
the app components be modeled as CloudFormation, Terraform, or
AppRegistry. Schedule monthly assessments to detect drift.

## Output format (STRICT output contract)

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
  1. <step 1>
  2. <step 2>
```

### Worked example — AUTOMATED pilot light
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
  - [WARN] DRS source servers: 4 of 5 in sync, 1 lagging
REMEDIATION:
  1. Re-sync lagging DRS source server i-0primary5
  2. Add ElastiCache cross-region replication for session state
```

### Worked example — MANUAL_STEP_REQUIRED (no verification)
```text
STRATEGY: warm-standby
RTO_TARGET: 5
RPO_TARGET: 1
REGIONS: primary=us-east-1, secondary=us-west-2
FAILOVER:
  - [PASS] Route 53 health check configured
  - [FAIL] No primary verification step — failover proceeds on first health check failure
  - [PASS] RDS cross-region read replica promotion defined
  - [PASS] DNS update via Route 53 API
  - [FAIL] No post-failover verification — clients may hit broken secondary
ORCHESTRATION:
  - [PASS] Step Functions state machine
  - [FAIL] No kill-switch
  - [FAIL] No human approval gate — fully automatic on first health failure
VERIFICATION:
  - [FAIL] No game-day drill in the last 12 months
  - [WARN] Resilience Hub assessment: 65 (below 80 target)
  - [WARN] Health check threshold 1 (too sensitive — false positives)
VERDICT: MANUAL_STEP_REQUIRED
FINDINGS:
  - [CRITICAL] No primary verification: a transient health check failure
    triggers full failover with no split-brain protection.
  - [CRITICAL] No kill-switch: a misconfigured health check endpoint causes
    automatic failover to an untested secondary.
  - [HIGH] No drill in 12 months: warm standby may have drift (stale AMIs).
  - [HIGH] No post-failover verification: clients routed to broken secondary.
REMEDIATION:
  1. Add dr-verify-primary-down Lambda as the first state; abort if primary is healthy.
  2. Add kill-switch Parameter Store /dr/kill-switch checked first.
  3. Run a game-day drill; document RTO measured.
  4. Tune health check threshold from 1 to 3.
```

## NEVER (these things)

- NEVER failover without first verifying the primary is truly down. A
  transient health check failure (network blip, brief ALB 5xx) triggers
  promotion of the secondary while the primary is still serving writes
  — split-brain, data divergence, irrecoverable state. Always run a
  verify-primary-down step with retries before promoting.

- NEVER skip the game-day drill. An untested failover plan is a wish.
  Aurora Global failover, RDS replica promotion, DRS launch — all have
  subtle behaviors (lag, IAM, launch template drift) that surface only
  on first execution. Run drills quarterly; document the measured RTO.

- NEVER rely on a single Route 53 health check as the failover trigger.
  Health checks have false positives (network blips, health endpoint
  bugs). Use a verification Lambda + Step Functions with retries as the
  actual trigger, not the health check directly.

- NEVER auto-failover without a kill-switch. A misconfigured health
  check endpoint causes endless failover flapping. The kill-switch lets
  you stop the orchestrator while debugging.

- NEVER assume Aurora Global failover is automatic. Out of the box,
  Aurora Global does NOT auto-failover. Managed Planned Failover (2024)
  handles the planned case; unplanned requires manual or Step Functions
  orchestration via `remove-from-global-cluster`.

## Expert heuristic callouts

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

## Pre-flight safety checks

- **MANDATORY CONFIRMATION GATE.** Before any state-changing DR operation
  (`rds failover-global-cluster`, `drs start-recovery`, `route53
  change-resource-record-sets` for failover), emit:
  `CONFIRM: About to <action> for <component> from <primary> to
  <secondary>. Proceed? (yes/no)` and wait for explicit `yes`.
- **Dry-run with `is_drill=true`.** DRS supports drill mode; Aurora
  Global supports managed planned failover. Always drill before going
  live with the orchestrator.
- **Verify the kill-switch is enabled.**
  `aws ssm get-parameter --name /dr/kill-switch` should return `enabled`.
- **Verify health check endpoints respond 200 in both regions.**
- **Verify the rollback path.** Aurora Global reverse requires snapshot
  rebuild; RDS requires re-snapshot. Plan ahead.
- **Verify the on-call notification path.** Send a test SNS message —
  unconfirmed subscriptions silently drop notifications.

## Edge-case handling

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

## Recent AWS features (2024-2026)

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

## Domain

AWS CloudOps / Disaster Recovery Failover Automation.

## AWS documentation

- **AWS Disaster Recovery** — https://docs.aws.amazon.com/wellarchitected/latest/disaster-recovery/
- **AWS Elastic Disaster Recovery** — https://docs.aws.amazon.com/drs/latest/userguide/
- **AWS Resilience Hub** — https://docs.aws.amazon.com/resilience-hub/latest/userguide/
- **Amazon Aurora Global Database** — https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/aurora-global-database.html
- **AWS Backup** — https://docs.aws.amazon.com/aws-backup/latest/devguide/
- **Amazon Route 53 Health Checks** — https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/dns-failover.html
- **AWS Global Accelerator** — https://docs.aws.amazon.com/global-accelerator/latest/dg/
- **AWS Step Functions** — https://docs.aws.amazon.com/step-functions/latest/dg/
- **AWS DR Blog** — https://aws.amazon.com/blogs/architecture/
