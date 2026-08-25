# Advanced Patterns — QuickSight Dashboard Deployer

Deep-dive material moved out of the SKILL.md body so the procedure stays scannable. Loaded on demand.


## Common misconceptions (from Mindset)

- **"Direct Query gives real-time data, so always use it."** It does
  give fresh data, but at the cost of query latency and source-store
  load. SPICE caches data in-memory and serves sub-second queries
  without hitting the source. For dashboards with many concurrent
  viewers or complex joins, Direct Query overwhelms the source
  database. The default for most dashboards should be SPICE with a
  scheduled refresh.

- **"Sharing a dashboard grants data access."** It does not. Sharing a
  dashboard lets a reader view the published version. Row-level
  security is a SEPARATE configuration that controls which rows each
  reader sees. Without RLS, every reader sees all data in the dataset.

- **"Templates are just for reuse."** Templates are the primary
  mechanism for multi-tenant dashboard deployment. A single template
  encodes the analysis definition; each tenant gets a dashboard created
  from that template pointing at its own dataset. This is far more
  scalable than manually rebuilding dashboards per tenant.


## Configuration dependency graph — sequencing notes

QuickSight dashboard configurations are NOT independent. The data source
must exist before the dataset. The dataset must exist before the
analysis. The analysis must exist before the dashboard. SPICE ingestion
must be configured before the refresh schedule. The VPC connection must
be authorized before private data sources can be used. Use this graph to
sequence provisioning.


## Cross-dependency gotchas

**Cross-dependency gotchas:**
- The VPC connection requires Enterprise edition. Standard edition
  cannot connect to private data stores.
- RLS is defined on the DATASET, not the dashboard. All dashboards
  using that dataset inherit the same RLS. For per-dashboard RLS, use
  separate datasets.
- Template deployment across accounts requires the target account to
  have its own QuickSight account and matching dataset schema.
- SPICE capacity is shared across ALL datasets in the account. Adding
  a large dataset may exhaust capacity for existing datasets.
- Dashboard sharing requires the reader's email to be registered as a
  QuickSight user. Unregistered emails cannot receive shares.


## Expert heuristic: SPICE vs Direct Query

A baseline model says "use Direct Query for real-time." The correct
heuristic evaluates cost, latency, concurrency, and freshness together.

```text
Dataset query mode decision:
  ├── Dashboard audience > 20 concurrent viewers → SPICE (avoid source overload)
  ├── Source DB is Aurora/RDS (limited connections) → SPICE (offload queries)
  ├── Data freshness requirement < 15 minutes → Direct Query (SPICE refresh min is 15 min)
  ├── Data volume > SPICE capacity (500GB Enterprise) → Direct Query (SPICE can't fit)
  ├── Complex joins / calculated fields across large tables → SPICE (pre-computed)
  ├── Redshift / Athena source (designed for analytical load) → Direct Query OK
  └── Cost-sensitive, low-traffic internal dashboard → Direct Query (no SPICE cost)
```

**Key implication:** the #1 cause of QuickSight dashboard performance
issues is Direct Query on an OLTP database (RDS/Aurora) with many
concurrent viewers. Switching to SPICE with a 15-minute refresh
eliminates source-store load and serves sub-second queries.


## Expert heuristic: RLS via dataset permissions and session identity

Row-level security is enforced at the dataset level. Two mechanisms:

```text
RLS mechanisms:
  1. Dataset permissions (Grant):
     - Define which rows a user/group can see based on a column value
     - QuickSight matches the user's identity against the RLS rules
     - Applied BEFORE data reaches the visual

  2. Session policy (generate-embedding-url-for-registered-user):
     - Used with embedded dashboards
     - Session identity passed via QuickSight reader session
     - RLS rules filter rows based on the session identity
```

**Multi-tenant pattern:** create one dataset per tenant with RLS rules
that filter by tenant ID. All tenants share the same template-based
dashboard definition but see only their own data.


## Expert heuristic: template-driven multi-tenant deployment

```text
Template deployment flow:
  1. Build the analysis + dashboard in a source account
  2. Create a template from the source analysis/dashboard
  3. For each tenant:
     a. Create a dataset in the tenant's namespace pointing at tenant data
     b. Create a dashboard FROM the template, referencing the tenant dataset
     c. Apply RLS rules on the tenant dataset
     d. Share the dashboard with tenant users
  4. Template updates: create new template version, then update all
     tenant dashboards from the new version
```

**Key implication:** a single template update propagates to all tenant
dashboards. This is the only scalable way to manage 10+ tenant
dashboards. Manual per-tenant rebuilds are error-prone.
