# 6R Strategy and Wave Planning Reference

Supplementary reference for the Migration Hub Strategy Deployer skill.
Use when interpreting 6R strategy output, planning migration waves from
dependency data, or sequencing the MGN/DMS handoff.

## 6R strategy classification

Strategy Recommendations assigns one of six strategies per application
(or per server if dependencies are missing):

| Strategy | Definition | Typical trigger |
|---|---|---|
| Rehost | Lift-and-shift to EC2, minimal changes | Default — no anti-patterns, no replatform driver |
| Replatform | Move to a managed AWS service with minor changes | EOL OS upgrade, self-managed DB to RDS/Aurora |
| Refactor | Redesign for cloud-native architecture | Scalability driver, monolith decomposition |
| Repurchase | Move to SaaS or different product | Commercial product replacement |
| Retain | Keep on-premises or defer | Compliance constraint, near-sunset, hard dependency |
| Retire | Decommission | Zero utilization detected by Discovery |

## Confidence levels

| Confidence | Meaning | Action |
|---|---|---|
| High | Sufficient data (7+ days, agent installed, no ambiguity) | Proceed with the strategy |
| Medium | Some data gaps (shorter window, agentless fallback for some hosts) | Validate with stakeholders before proceeding |
| Low | Insufficient data (agentless-only, short window, or stale vCenter data) | Do NOT proceed — collect more data |

## Anti-pattern detection reference

| Anti-pattern | Detection source | Strategy impact | Required action |
|---|---|---|---|
| EOL OS (Windows Server 2012 R2, CentOS 7, etc.) | Agent OS version | Forces replatform | Upgrade OS during migration |
| Deprecated DB engine (Oracle 11g, SQL Server 2008) | Agent DB engine detection | Forces replatform or repurchase | Upgrade DB or move to managed service |
| Kernel version gap | Agent kernel version | May block MGN agent | Update kernel before MGN setup |
| Bare-metal host | vCenter host type | Rehost not possible | Virtualize first |
| Excessive resource allocation | Agent utilization percentiles | Right-size recommendation | Downsize EC2 instance type |
| High network dependency (100+ connections) | Agent network data | Wave sequencing constraint | Migrate as part of a dependency cluster |

## Wave planning methodology

### Inputs

| Input | Source |
|---|---|
| Dependency graph | Discovery agent network data |
| Application grouping | Strategy Recommendations group-by-application |
| Business priority | Stakeholder input |
| Risk tolerance | Stakeholder input |
| Cutover window | Stakeholder input |

### Wave sequencing algorithm

1. Build the dependency graph from agent network data (nodes = servers,
   edges = network connections).
2. Find connected components (clusters of interdependent servers).
3. Identify shared services (DNS, AD, monitoring) — these are Wave 1.
4. Identify standalone applications (no edges) — these are Wave 0.
5. For each remaining cluster, assign a wave based on:
   - Dependencies on shared services (must be after Wave 1)
   - Dependencies on other clusters (merge into the same wave)
   - Business priority (higher priority earlier)
6. Validate: no wave splits a dependency cluster.

### Wave plan validation checklist

| Check | How to verify |
|---|---|
| No split dependency clusters | For each edge (A, B) in the graph, A and B are in the same wave |
| Shared services migrated first | DNS, AD, monitoring are in Wave 1 |
| Pilot is standalone | Wave 0 has no external dependencies |
| Retained apps have connectivity | VPN/Direct Connect planned for retained apps |

### Wave plan template

```text
WAVE 0 (pilot): <standalone application> — 1-2 servers, validate pipeline
WAVE 1 (foundation): <shared services> — DNS, AD, monitoring
WAVE 2: <cluster A> — depends on Wave 1 services
WAVE 3: <cluster B> — depends on Wave 1 and Wave 2
WAVE N: <complex or retained> — high-dependency or compliance-constrained
```

## MGN handoff checklist (rehost)

| Step | Command / action |
|---|---|
| Install MGN agent on source | Per OS (yum, apt, MSI) |
| Verify replication healthy | `aws mgn describe-replication-configuration-templates` |
| Configure launch template | Instance type, subnet, security group |
| Run test cutover | `aws mgn start-cutover --source-server-id s-xxxx` |
| Validate test instance | Application smoke tests |
| Schedule production cutover | Stakeholder approval + maintenance window |

## DMS handoff checklist (replatform)

| Step | Command / action |
|---|---|
| Run AWS SCT (heterogeneous only) | SCT GUI or CLI for schema conversion |
| Create source endpoint | `aws dms create-endpoint --endpoint-type source ...` |
| Create target endpoint | `aws dms create-endpoint --endpoint-type target ...` |
| Create migration task | `aws dms create-replication-task ...` |
| Start full load + CDC | `aws dms start-replication-task --migration-type full-load-and-cdc` |
| Validate data parity | Row counts + checksums |
| Cutover application | Update connection strings |

## Common wave planning failures

| Failure | Root cause | Fix |
|---|---|---|
| Wave splits a dependency cluster | Graph not checked before wave assignment | Re-run connected-components analysis |
| Shared service migrated late | Business priority overrode dependency logic | Move shared services to Wave 1 regardless of priority |
| Retained app breaks after wave | No VPN/Direct Connect plan for retained apps | Add network architecture for retained apps |
| EOL OS rehosted without upgrade | Anti-pattern ignored | Force replatform for EOL OS servers |
| DMS cutover with schema mismatch | SCT not run | Run SCT before DMS replication task |

---

## Appendix A — 6R strategy decision matrix (moved verbatim from SKILL.md)

| Signal | Rehost | Replatform | Refactor | Repurchase | Retain | Retire |
|---|---|---|---|---|---|---|
| No anti-patterns, low cloud driver | Yes | | | | | |
| EOL OS but app is stable | | Yes (upgrade OS) | | | | |
| Self-managed DB, want managed | | Yes (RDS/Aurora) | | | | |
| Need to scale, current arch limits | | | Yes | | | |
| Commercial product being replaced | | | | Yes (SaaS) | | |
| Compliance / hard constraint | | | | | Yes | |
| Zero utilization (Discovery) | | | | | | Yes |

