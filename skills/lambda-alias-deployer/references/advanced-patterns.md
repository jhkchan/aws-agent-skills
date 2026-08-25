# Advanced Patterns — Lambda Alias Deployer

Load-on-demand deep dives moved verbatim from SKILL.md.

## Mindset

**One-line takeaway:** A Lambda alias is a named pointer to a
specific published version of a function. It is the deployment
target for API Gateway, EventBridge, and other triggers. Traffic
shifting between versions uses weighted aliases, not in-place
updates. Provisioned concurrency and SnapStart are configured per
alias.

Three misconceptions dominate Lambda alias misdesign at provisioning
time:

- **"I can point an alias to $LATEST."** You should not. `$LATEST`
  is a mutable, versionless reference that changes on every update.
  Aliases should point to a PUBLISHED version (immutable snapshot).
  Pointing an alias to `$LATEST` defeats the purpose of version
  control: the alias target changes silently when the function is
  updated, bypassing the traffic-shift safety net.

- **"Traffic shifting means updating the function code."** It does
  not. Traffic shifting changes the WEIGHT on the alias to split
  traffic between two published versions. The function code is
  untouched. This is the foundation of canary and linear
  deployments: the new version is published first, then the alias
  weight gradually shifts from old to new.

- **"Provisioned concurrency goes on the function."** It can, but
  the best practice is to put it on the ALIAS, not the function or
  the version. Alias-level provisioned concurrency stays stable as
  you shift traffic: the provisioned capacity follows the alias,
  not a specific version. Version-level provisioned concurrency
  is lost when you re-point the alias.

## Configuration dependency graph (novel heuristic)

Lambda alias configurations are NOT independent. Many settings are
immutable after creation; others silently break traffic shifting or
provisioned concurrency. Use this graph to sequence provisioning
and debug "why is my alias not getting provisioned concurrency?"
later.

| Configuration | Hard dependencies (API error without) | Silent failure / immutability | Enables downstream |
|---|---|---|---|
| Published version | function exists + code deployed | version numbers are IMMUTABLE and auto-incremented | alias target |
| Alias | published version exists | alias name is immutable; version/weights are mutable | stable invocation target |
| Traffic weights | two published versions exist | weights must sum to 100%; shifting is progressive | canary/linear deployment |
| API Gateway integration | alias ARN with qualifier | changing the function behind the alias requires updating the API Gateway integration method | stable API endpoint |
| CloudWatch alarm | alias ARN (metric dimension) | alarm scoped to alias tracks only that version's errors | per-version monitoring |
| Provisioned concurrency | alias or version exists | **on alias: stable through traffic shifts**; on version: lost when alias re-points | cold-start elimination |
| SnapStart | function configured for SnapStart + published version | SnapStart snapshots are per-version; alias routing respects this | fast startup (JVM, Python) |
| Alias routing config | `UpdateAlias` with RoutingConfig | canary/linear weights are set on the alias, not the function | progressive rollout |

**The immutable rows are the ones a baseline model misses.**
Published version numbers are immutable and auto-incremented. Alias
names are immutable (must delete and re-create to rename). The
procedure below forces an explicit decision on each before the
`create-alias` call.

**Cross-dependency gotchas:**
- An alias CANNOT point to `$LATEST` for production traffic. It must
  point to a published version. Pointing to `$LATEST` means the
  alias target changes on every function update, defeating traffic
  shifting.
- Provisioned concurrency on a version is lost when the alias re-
  points. Always configure provisioned concurrency on the ALIAS,
  not the version.
- API Gateway integration uses the alias ARN with qualifier (e.g.,
  `function:prod`). If the alias is deleted, the API Gateway method
  breaks silently.
- SnapStart snapshots are per-version. When you shift traffic, each
  version has its own snapshot. The alias routes to the correct
  snapshot automatically.
- CloudWatch metrics with alias qualifier track only that alias's
  invocations. Without the qualifier, metrics are aggregated across
  all versions and `$LATEST`.

## Step 8 — Recent features detail (moved from SKILL.md)

**Recent AWS features (2023-2026):**

- **SnapStart for Python (2025-2026):** SnapStart extended beyond
  Java to Python 3.12. Same snapshot-based cold-start elimination
  for Python workloads.

- **SnapStart for Java 21 (2024-2025):** Extended SnapStart support
  to the Java 21 runtime.

- **Provisioned concurrency with Auto Scaling (2023-2024):**
  Application Auto Scaling now supports target-tracking policies for
  provisioned concurrency based on utilization. Dynamically adjusts
  provisioned environments without manual intervention.

- **CloudWatch Lambda Insights per alias (2023-2024):** Enhanced
  CloudWatch metrics with per-alias granularity, including memory
  utilization, CPU time, and cold-start counts scoped to each alias.

- **Lambda recursive detection (2023-2024):** AWS detects recursive
  Lambda loops and stops them automatically. Works with alias-based
  invocations.

- **Alias-based AWS X-Ray tracing (2023-2024):** X-Ray traces now
  include the alias qualifier, enabling per-alias trace analysis
  without separate instrumentation.
