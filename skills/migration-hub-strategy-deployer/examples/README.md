# End-to-end usage scenario: migration-hub-strategy-deployer

A walkthrough showing the skill producing a full migration assessment
plan for a 120-server portfolio: agent-based + agentless discovery,
14-day collection window, 6R strategy classification, anti-pattern
detection (EOL OS, deprecated DB), TCO analysis, wave planning from
the dependency graph, and MGN/DMS handoff. Demonstrates the
READY_TO_DEPLOY verdict and the three-stage pipeline (collect,
classify, sequence).

## Input (user prompt)

> Plan a Migration Hub Strategy assessment for our Q3 migration wave.
> We have 120 servers across 8 applications in vCenter. We want
> agent-based discovery on all critical hosts plus the agentless
> Collector. We expect EOL OS on srv-042 and a deprecated Oracle 11g
> on srv-078. Give us the full assessment plan with wave sequencing.

```
Design reference: portfolio-q3-assessment
Account: 111111111111
Home region: us-east-1
vCenter: vcenter.example.com (reachable on 443)

Portfolio: 120 servers across 8 applications.
Discovery: agent-based on 120 critical hosts + agentless Collector on vCenter.
Collection window: 14 days.
Anti-patterns expected: Windows Server 2012 R2 EOL (srv-042), Oracle 11g (srv-078).
MGN service role: configured. DMS replication instance: provisioned.
S3 report bucket: s3://migration-reports-111111111111/portfolio-q3/
```

## Skill output

```text
ASSESSMENT: portfolio-q3-assessment
HOME_REGION: us-east-1
DISCOVERY_METHOD:
  - Agent-based: yes, agent count 120 (all critical hosts)
  - Agentless: yes, Collector VM on vcenter.example.com
  - Collection window: 14 days
COLLECTOR_PLAN:
  - Prerequisites: vCenter 443 reachable, AWS 443 reachable, vCenter read credentials verified, DNS resolving
  - Deployment: OVA deployed, registered to home region us-east-1
ASSESSMENT_SCHEDULE:
  - Start: after-collection (14 days from Collector + agent deploy)
  - Duration: 14 days collection + 1 day analysis
  - Report bucket: s3://migration-reports-111111111111/portfolio-q3/
STRATEGY_GROUPS:
  - Application: billing-service, servers: 8, strategy: rehost, confidence: high
  - Application: user-auth, servers: 5, strategy: replatform (self-managed PostgreSQL to RDS), confidence: high
  - Application: legacy-crm, servers: 12, strategy: refactor (containerize), confidence: medium
  - Application: reporting-etl, servers: 0 active, strategy: retire, confidence: high
ANTI_PATTERNS:
  - Server: srv-042, pattern: EOL OS (Windows Server 2012 R2), impact: replatform to Windows Server 2022 required
  - Server: srv-078, pattern: deprecated DB engine (Oracle 11g), impact: replatform to Aurora PostgreSQL or upgrade
  - Server: srv-091, pattern: excessive resource allocation (P95 CPU 3%), impact: right-size from m5.4xlarge to m5.large
TCO:
  - On-premises 3-year: $1,800,000
  - AWS 3-year (right-sized): $1,100,000
  - Savings: $700,000 (39%)
RIGHT_SIZING:
  - Server: srv-091, current: 16 vCPU / 64 GB, recommended: m5.large (2 vCPU / 8 GB), utilization: P95 CPU 3%, mem 12%
WAVE_PLAN:
  - Wave 0 (pilot): billing-service (8 servers, no external dependencies)
  - Wave 1 (foundation): shared-dns, shared-ad, shared-monitoring (15 servers, all downstream depend on these)
  - Wave 2: user-auth (5 servers, depends on shared-ad from Wave 1)
  - Wave 3: legacy-crm (12 servers, depends on shared-dns and user-auth)
MGN_HANDOFF: ready (agent install instructions prepared for rehost targets)
DMS_HANDOFF: ready (SCT + DMS endpoints prepared for user-auth PostgreSQL replatform)
VERDICT: READY_TO_DEPLOY
GAP: None
TEMPLATE:
  # 1. Deploy Collector VM (agentless inventory)
  aws discovery start-import-task --name vcenter-import --vcenter --region us-east-1

  # 2. Install agents on 120 critical hosts (agent-based)
  # Per OS: yum install aws-discovery-agent / MSI / apt

  # 3. Wait 14 days, then start assessment
  aws migrationhub-strategy start-assessment --assessment-name portfolio-q3-assessment --s3bucket-for-report-data migration-reports-111111111111 --region us-east-1

  # 4. MGN rehost for billing-service
  aws mgn create-launch-template-template --launch-template-template-name billing-rehost --region us-east-1

  # 5. DMS replatform for user-auth PostgreSQL
  aws dms create-replication-instance --replication-instance-identifier user-auth-rep --replication-instance-class dms.r5.xlarge --region us-east-1
```

**Aggregate verdict: READY_TO_DEPLOY.** The full three-stage pipeline
(collect via agent + Collector, classify via Strategy Recommendations,
sequence via dependency-graph wave planning) is planned. MGN and DMS
handoffs are ready for the first wave.

## What the skill caught that a generic assistant misses

1. **The agent-based requirement for wave planning.** A generic
   assistant deploys agentless-only and assumes the 6R output is
   sufficient. The skill flags that without agent data, there is no
   dependency graph and wave planning is blocked.

2. **The 7-day minimum collection window.** A generic assistant starts
   the assessment immediately. The skill flags that right-sizing needs
   7+ days of utilization percentiles; a shorter window produces
   unreliable TCO.

3. **The EOL OS anti-pattern.** A generic assistant rehosts the Windows
   Server 2012 R2 server as-is. The skill detects the anti-pattern and
   forces a replatform (OS upgrade) in the wave plan.

4. **The SCT prerequisite for heterogeneous DMS.** A generic assistant
   jumps straight to DMS replication. The skill notes that Oracle-to-
   Aurora requires AWS SCT for schema conversion before DMS can
   replicate data.

5. **The shared-services-first wave rule.** A generic assistant
   sequences waves by business priority alone. The skill notes that
   shared services (DNS, AD, monitoring) must be Wave 1 regardless of
   priority — all downstream applications depend on them.

6. **The home-region immutability.** A generic assistant does not
   confirm the home region. The skill flags that changing the home
   region after collection starts requires re-importing all data.

## Slash-command invocation

```
/aws:deploy-migration-hub-strategy
```

Or via the orchestrator:

```
/aws:pipeline
You: "plan a migration assessment for 120 servers"
```

## CLI routing

```bash
node cli/bin/cli.js route "plan Migration Hub Strategy assessment"
# [Phase: Deploy | Skills routed: migration-hub-strategy-deployer]
```

## Live-account invocation (requires AWS CLI)

```bash
# Check existing Discovery agents
aws discovery describe-agents --region us-east-1 --profile default

# Check existing assessment status
aws migrationhub-strategy list-assessments --region us-east-1 --profile default

# Check portfolio preferences
aws migrationhub-strategy get-portfolio-preferences --region us-east-1 --profile default

# Check MGN source servers (for rehost readiness)
aws mgn describe-source-servers --region us-east-1 --profile default

# Check DMS replication instances (for replatform readiness)
aws dms describe-replication-instances --region us-east-1 --profile default

# Verify home region
aws migrationhub-strategy get-portfolio-preferences --region us-east-1 --profile default --query 'homeRegion'
```

Then paste the output into the skill for assessment planning.
