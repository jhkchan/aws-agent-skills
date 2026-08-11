---
name: migration-hub-strategy-deployer
description: >-
  Deploys AWS Migration Hub Strategy Recommendations assessments:
  assessment creation and group-by-application analysis, data collection
  via Application Discovery Service (agent-based for dependency telemetry
  vs agentless Collector VM for inventory), the 6R strategy
  classification (rehost, replatform, refactor, repurchase, retain,
  retire) from runtime telemetry, anti-pattern detection (EOL OS,
  deprecated DB engines), TCO analysis, right-sizing from utilization
  percentiles, migration wave planning from dependency mapping, and
  handoff to Application Migration Service (MGN) for rehost and Database
  Migration Service (DMS) for replatform. Emits READY_TO_DEPLOY with a
  Collector deployment plan and assessment schedule or
  PREREQUISITES_MISSING with the specific gap. Use when planning a
  migration assessment, deploying the Collector, interpreting 6R results,
  or sequencing migration waves.
version: 0.1.0
author: Jacky Chan — AWS Community Builder
license: Apache-2.0
compatibility: >-
  Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex,
  Gemini). No AWS CLI required for offline assessment planning. Live
  deployment uses aws migrationhub-strategy start-assessment,
  get-assessment, list-assessment, aws discovery describe-agents,
  describe-configurations, list-configurations, start-import-task,
  get-import-task, aws migrationhuborchestrator create-workflow,
  and aws mgn create-launch-template-template — AWS CLI v2, SSO or
  key-based credentials, Discovery and Migration Hub permissions in the
  home region.
keywords:
  - AWS Migration Hub
  - Strategy Recommendations
  - Application Discovery Service
  - ADS
  - Agent-based discovery
  - Agentless discovery
  - Collector VM
  - vCenter
  - 6R strategy
  - rehost
  - replatform
  - refactor
  - repurchase
  - retain
  - retire
  - anti-pattern detection
  - end-of-life OS
  - deprecated DB engine
  - TCO analysis
  - right-sizing
  - migration wave planning
  - dependency mapping
  - Application Migration Service
  - MGN
  - Database Migration Service
  - DMS
tags: [aws-migration-hub, strategy-recommendations, application-discovery-service, collector, 6r-strategy, wave-planning, mgn, dms, deploy]
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: true
  phase: 1
  supports_pipeline: true
  entry_point: false
  family: Migration
  task_type: deploy
  skill_class: capability
  lifecycle_status: active
  verdict_shape: "READY_TO_DEPLOY | PREREQUISITES_MISSING"
  when_to_use: >-
    Planning a Migration Hub Strategy Recommendations assessment,
    deploying the Application Discovery Service Collector (agent-based
    or agentless), interpreting 6R strategy classifications from runtime
    telemetry, detecting anti-patterns (end-of-life OS, deprecated DB
    engines), running a TCO analysis, right-sizing instances from
    utilization data, planning migration waves from dependency maps, or
    handing off to Application Migration Service (MGN) and Database
    Migration Service (DMS) for execution.
  activation_triggers:
    - "create Migration Hub Strategy assessment"
    - "deploy Discovery Collector"
    - "agent-based vs agentless discovery"
    - "6R strategy classification"
    - "rehost replatform refactor repurchase retain retire"
    - "anti-pattern detection end-of-life OS"
    - "deprecated DB engine migration"
    - "TCO analysis migration"
    - "right-sizing recommendations"
    - "migration wave planning"
    - "dependency mapping migration"
    - "Application Migration Service MGN handoff"
    - "Database Migration Service DMS replatform"
  invocation_schema: >-
    Input shape (one of): (a) a migration assessment specification
    including data source (agent-based, agentless import, or existing
    Discovery data), target applications or servers, assessment duration,
    and strategy preferences; (b) a partial spec for interactive
    refinement ("assess 200 vCenter VMs for 6R strategy"); (c) existing
    assessment results for interpretation and wave planning. Output shape:
    { ASSESSMENT_SPEC, VERDICT, COLLECTOR_PLAN, ASSESSMENT_SCHEDULE,
    STRATEGY_GROUPS[], ANTI_PATTERNS[], WAVE_PLAN, FINDINGS[] } where
    VERDICT is READY_TO_DEPLOY (Collector plan and assessment ready) or
    PREREQUISITES_MISSING (specific gap cited).
---

# Migration Hub Strategy Deployer

## Mindset

**One-line takeaway:** a migration strategy assessment is a three-stage
pipeline — **collect** (Application Discovery Service gathers inventory,
performance, and network dependency telemetry via agent-based Collectors
or agentless import) → **classify** (Strategy Recommendations derives
the 6R strategy per application from runtime data and anti-pattern
detection) → **sequence** (wave planning groups applications by
dependency proximity and risk into deployable migration waves). A gap
in ANY stage produces a silent failure: the Collector is deployed but
never reports data, the assessment runs but classifies everything as
"rehost" because utilization data is missing, or the wave plan ignores
a hard dependency and the first wave breaks a downstream application.

- **Agent-based discovery** collects process, performance, and network
  connection data but requires installing the Discovery Agent on every
  in-scope host. The deployment is invasive and may require a reboot.
  Without agent data, Strategy Recommendations cannot derive dependency
  maps or right-sizing — the assessment falls back to inventory-only.
- **Agentless discovery** via the Collector VM on vCenter gathers VM
  inventory and basic performance without guest-level agents, but it
  CANNOT capture process-level dependencies or inter-host network
  connections. Dependency mapping requires agent-based data or a
  separate network-flow source.
- **Anti-pattern detection** is the highest-value output of Strategy
  Recommendations: it flags end-of-life operating systems, deprecated
  database engines, and kernel-version gaps that force a replatform or
  refactor rather than a simple rehost. Ignoring anti-patterns and
  rehosting an end-of-life OS produces an EC2 instance that fails
  compliance on day one.

## Quick navigation

| You want to... | Go to |
|---|---|
| Pick between agent-based and agentless discovery | Step 1 + trade-off table |
| Deploy the Collector VM on vCenter | Step 2 + worked CLI |
| Configure the assessment scope and duration | Step 3 |
| Interpret the 6R strategy classification | Step 4 + Appendix A |
| Detect anti-patterns (EOL OS, deprecated DB) | Step 5 |
| Run TCO analysis and right-sizing | Step 6 |
| Plan migration waves from dependency data | Step 7 |
| Hand off to MGN for rehost execution | Step 8 |
| Hand off to DMS for database replatform | Step 9 |
| Avoid common Collector and assessment pitfalls | Anti-Patterns |
| Recent features (Strategy Recommendations API, MGN wave builder) | Recent AWS features |

## Critical rules at a glance (do NOT bury these)

1. **Agent-based discovery is required for dependency mapping.**
   Agentless (Collector VM) gathers inventory and basic performance but
   CANNOT capture inter-host network connections. If the wave plan
   depends on dependency data, agents must be installed on all in-scope
   hosts before the assessment starts.
2. **Strategy Recommendations needs 7+ days of utilization data for
   right-sizing.** The assessment derives EC2 instance recommendations
   from utilization percentiles. A 1-day collection produces noisy
   recommendations; the minimum recommended window is 7 days, with 14-30
   days preferred for seasonal workloads.
3. **The Discovery Collector VM requires network connectivity to BOTH
   the vCenter and AWS (the home region).** A Collector that cannot
   reach vCenter cannot import inventory; a Collector that cannot reach
   AWS cannot upload data. Both firewalls must be open before the
   Collector starts.
4. **MGN replication requires the source server's root volume to be
   accessible and the MGN agent installed.** A rehost strategy is not
   "done" when the 6R says rehost — it is done when MGN replication is
   healthy and a test cutover succeeds.
5. **DMS replatform requires the source and target database engines to
   be compatible.** Strategy Recommendations may recommend replatform
   from Oracle to Aurora PostgreSQL, but DMS schema conversion (via AWS
   SCT) is a prerequisite. The assessment does not run SCT automatically.

## Pre-flight: data requirements

Planning a Migration Hub Strategy assessment requires these inputs:

| Input | Source | Why |
|---|---|---|
| Home region | `aws migrationhub-strategy get-portfolio-preferences` (region-aware) | Migration Hub is region-scoped; all data lands in the home region |
| Existing Discovery data | `aws discovery describe-agents` / `list-configurations` | Avoid re-collecting if agents are already deployed |
| vCenter connectivity | Network firewall rules | Collector VM must reach vCenter on 443 |
| Application inventory | CMDB, spreadsheet, or vCenter VM list | Defines the assessment scope |
| MGN service role | `iam get-role` on `AWSApplicationMigrationAgentInstallationRole` | Rehost handoff requires MGN to be set up |
| DMS endpoints | `aws dms describe-endpoints` | Database replatform requires source and target endpoints |
| Strategy preferences | `migrationhub-strategy get-portfolio-preferences` | Configure rehost/replatform/refactor weighting |

**If the input is malformed** (missing vCenter or agent list, ambiguous
home region), emit:

```text
ASSESSMENT: <reference>
VERDICT: ERROR
REASON: Cannot plan assessment — data source and application inventory are required.
GAP: Re-supply the discovery method (agent-based / agentless), the application or server list, and the target home region.
```

## Process — Assessment planning (apply in order, produce deployment plan)

### Step 0: Expert knowledge — non-obvious Discovery and Strategy behaviors

These behaviors change the assessment plan if ignored:

- **The Discovery Collector VM is an OVA deployed on vCenter or a
  self-managed hypervisor.** It is NOT an AWS-managed service. The
  operator downloads the OVA from the AWS console, deploys it, and
  registers it with the Migration Hub home region. The Collector runs
  in the on-premises environment and uploads data to AWS.

- **Agent-based and agentless discovery are complementary, not
  alternatives.** Agentless (Collector VM) provides inventory and basic
  performance; agents provide process-level and network-connection
  detail. For a complete assessment, deploy BOTH: the Collector for
  inventory and the agents on critical hosts for dependencies. The
  Discovery service merges the data.

- **Strategy Recommendations requires a minimum data volume to classify
  strategy.** A server with less than 24 hours of performance data is
  classified as "rehost" by default (insufficient data to recommend
  right-sizing or replatform). For meaningful 6R classification, wait
  until at least 7 days of data are collected before starting the
  assessment.

- **The 6R classification is per-application, not per-server.** Strategy
  Recommendations groups servers into applications using dependency
  data. If dependencies are missing (agentless-only discovery), every
  server is treated as a standalone application and the 6R output is
  per-server. This loses the application-context strategy.

- **Anti-pattern detection runs on the OS and DB engine version
  reported by the Discovery agent.** If the agent is not installed, the
  OS version comes from vCenter tools, which may be stale. An EOL OS
  that vCenter reports as current produces a false-negative
  anti-pattern. Always cross-check with agent-based data.

- **MGN replication begins when the MGN agent is installed on the
  source server and the source server is registered to the MGN service
  in the home region.** The 6R "rehost" recommendation does not
  auto-install MGN. The operator must deploy the agent, configure
  replication settings, and validate a test cutover before the actual
  cutover.

- **DMS tasks for database replatform require AWS Schema Conversion Tool
  (SCT) to run first for heterogeneous migrations** (Oracle to Aurora,
  SQL Server to Aurora, etc.). SCT converts schema objects and stored
  procedures; DMS replicates the data. The Strategy Recommendations
  output flags the need for SCT but does not run it.

- **The home region is set once and cannot be changed without losing
  all Discovery data.** If the operator selects us-east-1 as the home
  region and later wants eu-west-1, all collected data must be
  re-imported. Always confirm the home region with stakeholders before
  starting collection.

- **Migration Hub Orchestrator (introduced 2023-2024) provides managed
  workflow templates for common migration patterns** (Windows rehost,
  Linux rehost, database replatform). These templates integrate with
  MGN and DMS and reduce the manual step count. Check whether a managed
  template fits the application profile before building a custom
  workflow.

### Step 1: Choose the discovery method

| Dimension | Agent-based (Discovery Agent) | Agentless (Collector VM) |
|---|---|---|
| Installation | Agent on each guest OS | OVA on vCenter or hypervisor |
| Inventory data | Yes | Yes |
| Performance data | Process-level (CPU, memory, disk per process) | VM-level (CPU, memory, disk for the whole VM) |
| Network dependency mapping | Yes (process-to-process connections) | No (VM-level only) |
| Guest OS access required | Yes (install agent) | No |
| Reboot required | Sometimes (driver install on Windows) | No |
| Best for | Dependency mapping, right-sizing, application grouping | Quick inventory, vCenter-only environments |
| Minimum collection window for 6R | 7 days | 7 days (but 6R falls back to rehost without dependencies) |

**Decision rule:** deploy agent-based discovery on all critical
applications (those with inter-host dependencies, databases, or
right-sizing uncertainty). Deploy agentless for the long tail of
standalone VMs where inventory-only is sufficient. The two data sources
merge in Discovery.

### Step 2: Deploy the Discovery Collector (agentless)

Download the Collector OVA from the Migration Hub console and deploy on
vCenter:

```bash
# Register the Collector with the home region after OVA deployment
aws discovery associate-configuration-items-to-application \
  --application-configuration-configuration-id app-xxxxxxx \
  --configuration-ids ["i-xxxxxxx"] \
  --region us-east-1
```

Collector prerequisites checklist:

| Prerequisite | How to verify | Effect if missing |
|---|---|---|
| vCenter reachability (443) | `nc -zv vcenter.example.com 443` | Collector cannot import inventory |
| AWS reachability (443 to home region) | `nc -zv migrationhub-strategy.us-east-1.amazonaws.com 443` | Collector cannot upload data |
| vCenter credentials with read access | Test login | Collector cannot enumerate VMs |
| Collector VM network with DHCP or static IP | vCenter console | Collector cannot communicate |
| DNS resolution for AWS endpoints | `nslookup migrationhub-strategy.us-east-1.amazonaws.com` | Upload fails intermittently |

### Step 3: Configure and start the assessment

```bash
# Start the assessment (assumes Discovery data is already collected)
aws migrationhub-strategy start-assessment \
  --assessment-name portfolio-assessment-q3 \
  --s3bucket-for-report-data migration-reports-111111111111 \
  --region us-east-1
```

Assessment scope and duration:

| Parameter | Recommended value | Why |
|---|---|---|
| Collection window before assessment | 7-14 days | Right-sizing needs percentile data |
| Assessment scope | All in-scope servers | Group-by-application requires full scope |
| S3 report bucket | Dedicated bucket with lifecycle policy | Reports are large; set 90-day expiration |
| Strategy preferences | Configure before starting | rehost vs replatform weighting affects output |

### Step 4: Interpret the 6R strategy classification

Strategy Recommendations assigns one of six strategies per application:

| Strategy | Meaning | When it is recommended |
|---|---|---|
| Rehost | Lift-and-shift to EC2 with minimal changes | Default when no anti-patterns detected and no replatform driver |
| Replatform | Move to a managed AWS service with minor changes (e.g., EC2 to Elastic Beanstalk, self-managed DB to RDS) | When a managed service reduces operational overhead without code changes |
| Refactor | Redesign the application for cloud-native architecture | When the application has a strong cloud-native driver (scalability, cost) |
| Repurchase | Move to a SaaS or different product | When the current product is being replaced (e.g., commercial CRM to SaaS) |
| Retain | Keep on-premises or defer migration | When the application is sunsetting soon or has hard compliance constraints |
| Retire | Decommission the application | When the application is unused (Discovery shows zero activity) |

**Key insight:** the 6R is a starting point, not a mandate. Operators
should validate each recommendation against business context. A rehost
recommendation for a stateful monolith may be technically correct but
strategically wrong if the business wants to refactor for scalability.

### Step 5: Detect anti-patterns

Strategy Recommendations flags anti-patterns that affect the strategy:

| Anti-pattern | Detection signal | Strategy impact |
|---|---|---|
| End-of-life OS (e.g., Windows Server 2012 R2, CentOS 7) | OS version from agent or vCenter | Forces replatform (upgrade OS) or refactor (containerize) |
| Deprecated DB engine (e.g., Oracle 11g, SQL Server 2008) | DB engine version from agent | Forces replatform (upgrade DB) or repurchase (move to managed) |
| Kernel version gap | Linux kernel version | May block MGN agent compatibility; update required |
| Bare-metal host | vCenter host type | Rehost not possible; must virtualize first |
| Excessive resource allocation | Utilization < 10% peak | Right-sizing recommendation; rehost with smaller instance |
| High network dependency (100+ connections) | Agent network data | Wave planning must sequence this application carefully |

### Step 6: TCO analysis and right-sizing

Strategy Recommendations generates a TCO comparison between on-premises
and AWS, based on:

- On-premises hardware cost (from the operator's input or defaults)
- AWS cost (from right-sized EC2 recommendations + EBS + data transfer)
- 3-year TCO horizon (default)

Right-sizing methodology:

| Utilization percentile | EC2 recommendation |
|---|---|
| P95 CPU < 20%, memory < 30% | Downsize by 2 sizes |
| P95 CPU 20-60%, memory 30-70% | Current size or one size down |
| P95 CPU > 80% or memory > 90% | Upsize or split |

**Gap class — missing utilization data:** if the collection window is
less than 7 days or the agent was not installed, right-sizing falls back
to a match-current-spec recommendation (on-premises vCPU/RAM mapped to
the closest EC2 instance). This over-provisions in most cases. Flag
`PREREQUISITES_MISSING` if the collection window is insufficient.

### Step 7: Plan migration waves from dependency data

Wave planning groups applications by dependency proximity. The goal is to
migrate interdependent applications together to avoid partial-migration
breakage.

Wave planning inputs:

| Input | Source |
|---|---|
| Application dependency graph | Discovery agent network data |
| Application grouping | Strategy Recommendations group-by-application output |
| Business priority | Stakeholder input |
| Risk tolerance | Stakeholder input |
| Cutover window constraints | Stakeholder input |

Wave sequencing heuristic:

1. **Wave 0 (pilot):** 1-2 low-risk, standalone applications (no
   dependencies). Validate the MGN/DMS pipeline end-to-end.
2. **Wave 1 (foundation):** shared services (DNS, AD, monitoring) that
   downstream applications depend on. These MUST migrate first.
3. **Wave 2+ (dependency-ordered):** applications grouped by dependency
   clusters. Each wave is a connected component in the dependency graph
   — migrating a wave must not leave a dependency stranded across the
   on-premises/AWS boundary.
4. **Wave N (complex):** applications with 100+ dependencies or hard
   compliance constraints. These require detailed runbooks and may use
   a hybrid model (retain on-premises with VPN/Direct Connect).

**Hard constraint:** a wave must not split a dependency cluster. If
application A (wave 2) depends on application B (wave 3), either move B
to wave 2 or delay A to wave 3. The dependency graph determines the
minimum wave count; business priority determines the ordering within
that constraint.

### Step 8: Hand off to Application Migration Service (MGN) for rehost

For applications classified as "rehost," MGN handles replication and
cutover:

```bash
# Install the MGN agent on the source server (requires OS access)
# On Linux:
sudo yum install aws-replication-agent -y

# Register the source server with MGN
aws mgn create-launch-template-template \
  --launch-template-template-name rehost-template \
  --region us-east-1
```

MGN handoff checklist:

| Step | Command / action |
|---|---|
| Install MGN agent | Per OS (yum, apt, MSI) |
| Verify replication healthy | `aws mgn describe-replication-configuration-templates` |
| Configure launch template | Set instance type, subnet, security group |
| Run test cutover | `aws mgn start-cutover --source-server-id s-xxxx` |
| Validate test instance | Application-level smoke tests |
| Schedule production cutover | Stakeholder approval + maintenance window |

### Step 9: Hand off to Database Migration Service (DMS) for replatform

For databases classified as "replatform" (self-managed to RDS/Aurora):

```bash
# Create the DMS replication instance
aws dms create-replication-instance \
  --replication-instance-identifier migration-rep \
  --replication-instance-class dms.r5.xlarge \
  --region us-east-1
```

DMS handoff checklist:

| Step | Command / action |
|---|---|
| Run AWS SCT for schema conversion | SCT GUI or CLI (heterogeneous migrations only) |
| Create source endpoint | `aws dms create-endpoint --endpoint-type source ...` |
| Create target endpoint | `aws dms create-endpoint --endpoint-type target ...` |
| Create migration task | `aws dms create-replication-task ...` |
| Start full load + CDC | `aws dms start-replication-task --migration-type full-load-and-cdc` |
| Validate data parity | Compare row counts and checksums |
| Cutover application connection | Update connection strings |

## Output format

```text
ASSESSMENT: <reference>
HOME_REGION: <region>
DISCOVERY_METHOD:
  - Agent-based: <yes | no>, agent count <N>
  - Agentless: <yes | no>, Collector VM on <vCenter / hypervisor>
  - Collection window: <days>
COLLECTOR_PLAN:
  - Prerequisites: <verified list>
  - Deployment: <OVA + registration steps>
ASSESSMENT_SCHEDULE:
  - Start: <immediate | after-collection>
  - Duration: <days>
  - Report bucket: <s3 uri>
STRATEGY_GROUPS:
  - Application: <name>, servers: <N>, strategy: <6R>, confidence: <high | medium | low>
ANTI_PATTERNS:
  - Server: <id>, pattern: <EOL OS | deprecated DB | ...>, impact: <replatform | refactor | ...>
TCO:
  - On-premises 3-year: <$X>
  - AWS 3-year (right-sized): <$Y>
  - Savings: <$Z>
RIGHT_SIZING:
  - Server: <id>, current: <vCPU/RAM>, recommended: <instance type>, utilization: <P95 CPU/mem>
WAVE_PLAN:
  - Wave 0: <pilot applications>
  - Wave 1: <foundation applications>
  - Wave 2+: <dependency-ordered clusters>
MGN_HANDOFF: <ready | blocked>
DMS_HANDOFF: <ready | blocked>
VERDICT: READY_TO_DEPLOY | PREREQUISITES_MISSING
GAP: <if PREREQUISITES_MISSING, the specific missing piece>
TEMPLATE: <CLI snippets for Collector, assessment, MGN, DMS>
```

### Worked example — READY_TO_DEPLOY, full assessment

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
  - Start: after-collection (14 days from Collector deploy)
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
  - Server: srv-042, current: 8 vCPU / 32 GB, recommended: m5.xlarge (4 vCPU / 16 GB), utilization: P95 CPU 45%, mem 60%
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
  # Download OVA from Migration Hub console, deploy on vcenter.example.com
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

### Worked example — PREREQUISITES_MISSING, agentless-only with short window

```text
ASSESSMENT: portfolio-q3-partial
HOME_REGION: us-east-1
DISCOVERY_METHOD:
  - Agent-based: no (agents not deployed)
  - Agentless: yes, Collector VM on vcenter.example.com
  - Collection window: 2 days
COLLECTOR_PLAN:
  - Prerequisites: vCenter 443 reachable, AWS 443 reachable
  - Deployment: OVA deployed, registered
ASSESSMENT_SCHEDULE:
  - Start: after-collection
  - Duration: 2 days collection + 1 day analysis
  - Report bucket: s3://migration-reports-111111111111/portfolio-q3/
STRATEGY_GROUPS:
  - Server: srv-001, strategy: rehost, confidence: low (fallback — no dependency data)
  - Server: srv-002, strategy: rehost, confidence: low (fallback — no utilization data)
ANTI_PATTERNS:
  - Server: srv-042, pattern: EOL OS (Windows Server 2012 R2), impact: replatform required
  - (other anti-patterns may be false-negative due to stale vCenter OS data)
TCO: insufficient data (right-sizing not possible without utilization percentiles)
RIGHT_SIZING: not available (fallback to match-current-spec)
WAVE_PLAN: not possible (no dependency graph)
MGN_HANDOFF: blocked
DMS_HANDOFF: blocked
VERDICT: PREREQUISITES_MISSING
GAP: Three blockers: (1) agent-based discovery not deployed — dependency mapping and application grouping are not possible, every server defaults to standalone rehost; (2) collection window is 2 days, below the 7-day minimum for right-sizing — TCO will be unreliable; (3) wave planning is blocked without dependency data. Install agents on critical hosts and extend the collection window to at least 7 days (14 preferred) before starting the assessment.
TEMPLATE: (partial — install agents, then re-run)
```

## Anti-Patterns — NEVER do these things

- NEVER start an assessment with less than 7 days of Discovery data. The
  right-sizing and 6R classification rely on utilization percentiles. A
  short window produces noisy recommendations that over-provision or
  under-provision, undermining stakeholder confidence in the migration.

- NEVER rely on agentless-only discovery for wave planning. The Collector
  VM provides inventory but NOT inter-host dependencies. Without the
  dependency graph, every server is a standalone application and wave
  sequencing is impossible. Install agents on critical hosts before the
  assessment.

- NEVER rehost an end-of-life OS without flagging the anti-pattern.
  Strategy Recommendations detects EOL OS versions and recommends
  replatform. Ignoring this and rehosting produces an EC2 instance that
  fails compliance and security baseline checks on day one. Always
  surface anti-patterns in the wave plan.

- NEVER assume the 6R strategy is final. Strategy Recommendations
  classifies from runtime telemetry; it does not know business context.
  A "rehost" recommendation for an application the business wants to
  refactor is a starting point for discussion, not a directive. Always
  validate the 6R with stakeholders.

- NEVER skip the MGN test cutover. A rehost strategy is not complete
  until MGN replication is healthy AND a test cutover produces a
  bootable, functional EC2 instance. A production cutover without a
  test is a single point of failure.

- NEVER skip AWS SCT for heterogeneous database migrations. DMS
  replicates data; it does NOT convert schema objects or stored
  procedures. An Oracle-to-Aurora replatform without SCT produces a
  database with tables but no triggers, views, or procedures.

- NEVER deploy the Collector VM without verifying vCenter and AWS
  network reachability. A Collector that cannot reach vCenter cannot
  import; a Collector that cannot reach AWS cannot upload. Both paths
  must be open before the OVA is deployed.

- NEVER change the Migration Hub home region after collection starts.
  All Discovery data is region-scoped. Changing the home region requires
  re-importing all data and re-deploying all agents. Confirm the region
  with stakeholders before starting.

- NEVER assume the Discovery agent's OS version data matches vCenter.
  vCenter tools may report a stale OS version (especially after a
  guest-side upgrade that did not update VMware tools). Anti-pattern
  detection is only as accurate as the OS version source. Always
  cross-check with agent-based data on critical hosts.

- NEVER wave-plan without the dependency graph. A wave that splits a
  dependency cluster (application A in wave 2 depends on application B
  in wave 3) creates a broken state where A cannot reach B across the
  on-premises/AWS boundary. The dependency graph defines the minimum
  wave count.

- NEVER start DMS replication without validating data parity after the
  full load. A full load that completes with row-count mismatches
  produces a target database that is silently incomplete. Always
  compare row counts and checksums before the cutover.

- NEVER interpret "retain" as "do nothing." A retain strategy means the
  application stays on-premises (or is deferred). It still requires a
  connectivity plan (VPN/Direct Connect) to reach migrated applications
  in AWS. Include retained applications in the network architecture.

- NEVER use Migration Hub Orchestrator managed templates without
  verifying they fit the application profile. The Windows rehost
  template assumes a specific MGN configuration; a Windows application
  with a custom service account or non-standard drive layout may need a
  custom workflow. Validate the template against one pilot application
  first.

- NEVER forget that Discovery data is eventually consistent in the
  Migration Hub console. A newly installed agent may take 15-30 minutes
  to appear in the console. Do not assume the agent failed; verify with
  `aws discovery describe-agents` before troubleshooting.

## Configuration dependency graph

The Migration Hub Strategy assessment has strict ordering dependencies.
Deploy out of order and components fail silently or produce unreliable
output.

```
[Confirm home region with stakeholders]
        |
        v
[Deploy Collector VM on vCenter (agentless inventory)]
        |
        +-----------------------------+
        |                             |
        v                             v
[Install Discovery agents on critical hosts]   [Verify vCenter + AWS network paths]
        |                             |
        v                             v
[Wait 7-14 days for utilization + dependency data]   [Discovery data merging in console]
        |                             |
        +-----------------------------+
        |
        v
[Start Strategy Recommendations assessment]
        |
        v
[Review 6R strategy + anti-patterns + TCO + right-sizing]
        |
        +-----------------------------+
        |                             |
        v                             v
[Wave planning from dependency graph]   [MGN setup for rehost targets]
        |                             |
        v                             v
[Wave 0 pilot cutover]                [DMS + SCT setup for replatform targets]
        |                             |
        v                             v
[Wave 1+ production cutover sequence]  [Database replatform cutover]
```

**Hard ordering constraints:**

1. The home region MUST be confirmed before any data collection. All
   Discovery data is region-scoped and cannot be moved.
2. The Collector VM MUST reach vCenter AND AWS before it can import or
   upload. Verify both paths before deployment.
3. Discovery agents MUST be installed before the collection window
   starts. Agents installed mid-window produce partial data for those
   hosts.
4. The assessment MUST NOT start until the collection window completes
   (7-14 days). Starting early produces unreliable right-sizing.
5. Wave planning MUST NOT proceed without the dependency graph
   (agent-based data). Agentless-only wave planning is blocked.
6. MGN test cutover MUST succeed before production cutover.

**Parallelizable:** (a) Collector VM deployment and agent installation
are independent; (b) MGN and DMS setup for different applications can
proceed in parallel once the 6R strategies are confirmed.

## Pre-flight safety checks (run before starting any assessment)

- **MANDATORY CONFIRMATION GATE.** Before any state-changing operation
  (`start-assessment`, `start-import-task`, MGN `start-cutover`, DMS
  `start-replication-task`), emit:
  `CONFIRM: About to <action> for assessment <name> in region <region>.
  This affects <consequence>. Proceed? (yes/no)`

- **Before deploying the Collector VM**, verify vCenter and AWS network
  paths are open. A Collector deployed without network paths appears
  healthy but never reports data.

- **Before starting the assessment**, verify the collection window is at
  least 7 days. Short windows produce unreliable right-sizing.

- **Before a production MGN cutover**, verify a test cutover succeeded
  and the test instance passed application-level smoke tests.

- **Before a DMS cutover**, verify data parity (row counts + checksums)
  between source and target.

## Appendix A — 6R strategy decision matrix

| Signal | Rehost | Replatform | Refactor | Repurchase | Retain | Retire |
|---|---|---|---|---|---|---|
| No anti-patterns, low cloud driver | Yes | | | | | |
| EOL OS but app is stable | | Yes (upgrade OS) | | | | |
| Self-managed DB, want managed | | Yes (RDS/Aurora) | | | | |
| Need to scale, current arch limits | | | Yes | | | |
| Commercial product being replaced | | | | Yes (SaaS) | | |
| Compliance / hard constraint | | | | | Yes | |
| Zero utilization (Discovery) | | | | | | Yes |

## Appendix B — Collector VM vs Discovery Agent deployment summary

| Dimension | Collector VM (agentless) | Discovery Agent |
|---|---|---|
| Form factor | OVA on vCenter/hypervisor | Per-guest install |
| Data depth | Inventory + VM performance | Process + network + performance |
| Guest access | No | Yes |
| Scale | vCenter scope (all VMs) | Per-host deployment |
| Dependency mapping | No | Yes |
| OS for anti-pattern | From vCenter tools (may be stale) | From guest (current) |

For the full Collector deployment walkthrough and agent install commands,
see **references/discovery-collector-deployment.md**. For the 6R
interpretation guide and wave planning templates, see
**references/strategy-and-wave-planning.md**.

## Recent AWS features (2024-2026)

- **Migration Hub Strategy Recommendations API (2024):** The
  `start-assessment`, `get-assessment`, and `list-assessment` APIs are
  now GA. Previously console-only. Programmatic assessment creation is
  now supported.
- **Migration Hub Orchestrator managed workflows (2024-2025):**
  Pre-built workflow templates for Windows rehost, Linux rehost, and
  database replatform reduce manual step count. Check template fit
  before building a custom workflow.
- **MGN wave builder (2024-2025):** MGN integrates with Strategy
  Recommendations to auto-populate wave groupings from the dependency
  graph. Reduces manual wave planning for rehost targets.
- **Application Discovery Service agent for ARM Linux (2024):** The
  Discovery agent now supports ARM-based Linux hosts, expanding
  inventory coverage for non-x86 environments.
- **DMS Serverless (2024-2025):** DMS Serverless auto-scales capacity
  for variable-load migrations, reducing the need to pre-provision
  replication instance sizes. Useful for replatform waves with
  unpredictable data volumes.

## Expert heuristic: agent-based vs agentless trade-off + 6R from telemetry + wave sequencing from dependency mapping

The most common migration assessment failure is NOT a missing Collector
— it is an assessment that produces unreliable output because
agent-based discovery was skipped and the wave plan was built without
the dependency graph.

**The rule (non-negotiable):**

> ALWAYS deploy agent-based discovery on all critical hosts (those with
> inter-host dependencies, databases, or right-sizing uncertainty)
> BEFORE starting the assessment. The 6R classification is only as good
> as the underlying telemetry: without agent data, every server defaults
> to standalone "rehost," anti-pattern detection may be based on stale
> vCenter OS data, and wave planning is blocked. The collection window
> must be at least 7 days (14 preferred) for reliable right-sizing.

**Why this rule exists:** Strategy Recommendations derives the 6R
strategy from three data sources: inventory (what the server is),
performance (how hard it works), and network (what it depends on).
Agentless discovery provides inventory and VM-level performance but
NOT network dependencies. Without dependencies, the service cannot
group servers into applications — every server is standalone, and the
6R output is per-server rehost. This produces a migration plan that
ignores inter-application dependencies and breaks on the first wave.

**Agent-based vs agentless decision matrix:**

| Application profile | Agent-based | Agentless | Rationale |
|---|---|---|---|
| Multi-tier with dependencies | Required | Optional (for inventory baseline) | Dependency graph is mandatory for wave planning |
| Standalone VM, no dependencies | Optional | Sufficient | No dependencies to map; inventory + performance is enough |
| Database server | Required | Optional | DB engine version must come from the guest for accurate anti-pattern detection |
| EOL OS candidate | Required | Optional | OS version from vCenter tools may be stale; agent data is current |
| Right-sizing candidate | Required | Optional | Process-level utilization percentiles need agent data |
| Large fleet (500+ VMs) | Critical hosts only | All VMs | Agent on all 500 is invasive; prioritize by criticality |

**Wave sequencing from dependency mapping:**

The dependency graph is a directed graph where nodes are servers and
edges are network connections (from agent data). Wave planning finds
connected components and migrates each component as a unit. The
minimum wave count is the number of connected components that cannot
be parallelized due to shared dependencies.

| Dependency pattern | Wave strategy | Risk |
|---|---|---|
| Standalone (no edges) | Wave 0 (pilot) | Low — no dependencies to break |
| Shared service (DNS, AD) | Wave 1 (foundation) | High — downstream apps depend on these; must migrate first |
| Connected cluster (N apps) | Wave N (whole cluster) | Medium — entire cluster migrates together; schedule a single cutover |
| Cross-cluster edge | Merge waves | High — a dependency across clusters forces them into the same wave |

**Detection of insufficient telemetry post-assessment:** if the 6R
output is 100% rehost with low confidence and the wave plan is empty,
the assessment ran without dependency data. Verify with
`aws discovery describe-agents` that agents reported data during the
collection window. If agent count is zero or data is sparse, re-run
the assessment after installing agents.

**Surface in the output:** for any recommended migration plan, include
`DISCOVERY_COVERAGE: <agent-based | agentless-only | mixed>`,
`COLLECTION_WINDOW: <days>`, `DEPENDENCY_GRAPH: <available | missing>`,
and `WAVE_CONFIDENCE: <high | medium | low>`. If
`DISCOVERY_COVERAGE` is `agentless-only` or `DEPENDENCY_GRAPH` is
`missing`, do NOT mark the plan as READY_TO_DEPLOY.

## Domain

AWS CloudOps / Migration — Strategy assessment and wave planning.

## AWS documentation

- **AWS Migration Hub Strategy Recommendations** — https://docs.aws.amazon.com/migrationhub-strategy/latest/userguide/
- **Application Discovery Service** — https://docs.aws.amazon.com/application-discovery/latest/userguide/
- **Application Migration Service (MGN)** — https://docs.aws.amazon.com/mgn/latest/
- **Database Migration Service (DMS)** — https://docs.aws.amazon.com/dms/latest/
- **AWS Schema Conversion Tool (SCT)** — https://docs.aws.amazon.com/SchemaConversionTool/latest/userguide/
- **Migration Hub Orchestrator** — https://docs.aws.amazon.com/migrationhub-orchestrator/latest/
