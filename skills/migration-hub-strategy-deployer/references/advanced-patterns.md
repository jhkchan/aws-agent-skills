# Migration Hub Strategy Deployer — advanced patterns (moved verbatim from SKILL.md)

> Progressive-disclosure split: this content was moved verbatim from SKILL.md; nothing was rewritten.

## Mindset — extended rationale (collect → classify → sequence failure modes)

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

## Step 0: Expert knowledge — non-obvious Discovery and Strategy behaviors

- **The Discovery Collector VM is an OVA deployed on vCenter, NOT an
  AWS-managed service.** The operator downloads, deploys, and registers
  it with the home region. It runs on-premises and uploads to AWS.

- **Agent-based and agentless discovery are complementary, not
  alternatives.** Agentless provides inventory and basic performance;
  agents provide process-level and network-connection detail. Deploy
  BOTH for a complete assessment. Discovery merges the data.

- **Strategy Recommendations needs 7+ days of data for meaningful 6R
  classification.** A server with less than 24 hours of data defaults to
  "rehost" (insufficient data for right-sizing or replatform).

- **The 6R classification is per-application, not per-server.** Strategy
  Recommendations groups servers into applications using dependency
  data. Without dependencies (agentless-only), every server is
  standalone and the 6R output loses application context.

- **Anti-pattern detection uses the OS and DB version from the agent.**
  Without agents, OS version comes from vCenter tools, which may be
  stale. An EOL OS reported as current by vCenter produces a
  false-negative anti-pattern.

- **MGN replication requires the MGN agent on the source and
  registration to the home region.** The "rehost" recommendation does
  not auto-install MGN. The operator deploys the agent, configures
  replication, and validates a test cutover.

- **DMS replatform requires AWS SCT first for heterogeneous migrations**
  (Oracle to Aurora, SQL Server to Aurora). SCT converts schema and
  stored procedures; DMS replicates data. Strategy Recommendations flags
  the need but does not run SCT.

- **The home region is set once and cannot be changed without losing all
  Discovery data.** Confirm with stakeholders before starting collection.

- **Migration Hub Orchestrator provides managed workflow templates** for
  common patterns (Windows rehost, Linux rehost, database replatform).
  Check template fit before building a custom workflow.

## Configuration dependency graph

The assessment has strict ordering dependencies — deploy out of order and
components fail silently or produce unreliable output.

```
[Confirm home region] → [Deploy Collector VM on vCenter]
        |
        +-----------------------------+
        |                             |
        v                             v
[Install agents on critical hosts]   [Verify vCenter + AWS 443 paths]
        |                             |
        +-----------------------------+
        |
        v
[Wait 7-14 days for utilization + dependency data]
        |
        v
[Start Strategy Recommendations assessment]
        |
        v
[Review 6R + anti-patterns + TCO + right-sizing]
        |
        +-----------------------------+
        |                             |
        v                             v
[Wave planning from dependency graph]   [MGN setup for rehost]
        |                             |
        v                             v
[Wave 0 pilot cutover]            [DMS + SCT setup for replatform]
        |                             |
        v                             v
[Wave 1+ production cutover]      [Database replatform cutover]
```

**Hard ordering constraints:**

1. Home region MUST be confirmed before any data collection (data is
   region-scoped and cannot be moved).
2. Collector VM MUST reach vCenter AND AWS (443) before deployment.
3. Agents MUST be installed before the collection window starts.
4. Assessment MUST NOT start until the collection window completes
   (7-14 days).
5. Wave planning MUST NOT proceed without the dependency graph.
6. MGN test cutover MUST succeed before production cutover.

**Parallelizable:** Collector deployment and agent installation are
independent. MGN and DMS setup for different applications can proceed
in parallel once the 6R strategies are confirmed.

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

## Expert heuristic: agent-based vs agentless trade-off + 6R from telemetry + wave sequencing

The most common migration assessment failure is NOT a missing Collector
— it is an assessment that produces unreliable output because
agent-based discovery was skipped and the wave plan was built without
the dependency graph.

**The rule (non-negotiable):**

> ALWAYS deploy agent-based discovery on all critical hosts (those with
> inter-host dependencies, databases, or right-sizing uncertainty)
> BEFORE starting the assessment. Without agent data, every server
> defaults to standalone "rehost," anti-pattern detection may use stale
> vCenter OS data, and wave planning is blocked. The collection window
> must be at least 7 days (14 preferred).

**Why this rule exists:** Strategy Recommendations derives the 6R
strategy from three sources: inventory, performance, and network
dependencies. Agentless provides inventory and VM-level performance but
NOT dependencies. Without dependencies, every server is standalone and
the 6R output is per-server rehost, producing a plan that ignores
inter-application dependencies and breaks on the first wave.

**Agent-based vs agentless decision matrix:**

| Application profile | Agent-based | Agentless | Rationale |
|---|---|---|---|
| Multi-tier with dependencies | Required | Optional | Dependency graph mandatory for wave planning |
| Standalone VM | Optional | Sufficient | No dependencies to map |
| Database server | Required | Optional | DB engine version must come from guest |
| EOL OS candidate | Required | Optional | vCenter OS data may be stale |
| Large fleet (500+) | Critical hosts only | All VMs | Prioritize by criticality |

**Wave sequencing from dependency mapping:** the dependency graph has
nodes (servers) and edges (network connections). Wave planning finds
connected components and migrates each as a unit. Standalone servers go
in Wave 0 (pilot). Shared services (DNS, AD) go in Wave 1 (foundation).
Connected clusters migrate together. Cross-cluster edges force clusters
into the same wave.

**Detection of insufficient telemetry:** if the 6R output is 100%
rehost with low confidence and the wave plan is empty, the assessment
ran without dependency data. Verify with `aws discovery describe-agents`.

**Surface in the output:** include `DISCOVERY_COVERAGE`,
`COLLECTION_WINDOW`, `DEPENDENCY_GRAPH`, and `WAVE_CONFIDENCE`. If
`DISCOVERY_COVERAGE` is `agentless-only` or `DEPENDENCY_GRAPH` is
`missing`, do NOT mark the plan as READY_TO_DEPLOY.

