# Advanced Patterns — Elastic Beanstalk Deployer

Expert heuristics, dependency-graph deep dives, misconception analysis, and recent AWS features moved verbatim from SKILL.md. Loaded on demand.

## Mindset misconceptions — full reasoning (from SKILL.md § Mindset)

- **"All-at-once deployment is fine for production."** It is not. All-
  at-once takes the entire fleet out of service simultaneously during
  the deploy. If the new version is broken, 100% of traffic fails.
  Immutable or rolling-with-additional-batch is the production-grade
  default because it preserves capacity during cutover.

- **".ebextensions are just configuration files."** They are not.
  .ebextensions are ordered infrastructure-as-code directives that can
  create ANY AWS resource (RDS, DynamoDB tables, SNS topics, IAM
  roles) via CloudFormation under the hood. Ordering matters: a
  directive in `01-setup.config` runs before `02-storage.config`, and
  a malformed directive silently aborts the deployment.

- **"CNAME swap is automatic."** It is not. Blue-green via CNAME swap
  requires TWO environments (green and blue), both fully deployed and
  healthy, and then a `SwapEnvironmentCNAMEs` API call. The swap is
  atomic at the DNS level, but the TTL of the old CNAME means clients
  may still hit the old environment for up to 60 seconds.

## Configuration dependency graph — deep-dive notes (from SKILL.md)

**The service-role-and-instance-profile row is the one a baseline model
misses.** Creating the environment without the correct service role and
instance profile either fails at creation time or results in a stuck
deployment where EC2 instances cannot pull the source bundle. The
deployment policy row is another commonly misunderstood configuration
— operators pick all-at-once for speed and discover the blast radius
only when a bad deploy takes down the entire fleet.

**Cross-dependency gotchas:**
- The service role and instance profile are separate IAM roles with
  separate trust policies. The service role is assumed BY Beanstalk;
  the instance profile is assumed BY the EC2 instances.
- Traffic splitting deployment policy requires an ALB. If the
  environment uses an NLB or single-instance (no ELB), traffic
  splitting is not available.
- Managed platform updates have a configurable window. If the window
  overlaps with a scheduled deployment, the managed update is
  suppressed until the next window.
- .ebextensions ordering is lexicographic: `01-config.config` runs
  before `02-config.config`. A resource created in `02-config.config`
  cannot be referenced in `01-config.config`.
- Worker tier environments do NOT have a load balancer. The SQS daemon
  runs on each instance and polls the queue.

## Expert heuristic: immutable deployment for zero downtime (from SKILL.md)

A baseline model says "deploy the new version." The correct heuristic
recognizes that the deployment policy determines the blast radius
during cutover.

```text
Deployment policy decision tree:
  ├── Development / testing → All at once (fastest, full downtime OK)
  ├── Production, single-instance → Immutable (launches fresh ASG, swaps)
  ├── Production, multi-instance, cost-sensitive → Rolling + additional batch
  │     (adds temp instances, deploys in batches, no capacity loss)
  ├── Production, multi-instance, canary needed → Traffic splitting
  │     (routes a percentage of traffic to the new version via ALB)
  └── Production, multi-instance, simplest rolling → Rolling
        (takes batches out of service, reduced capacity during deploy)

Key: "immutable" is safest for production because it launches an
entirely new fleet with the new version, verifies health, then swaps.
If health checks fail, the old fleet is untouched.
```

**Key implication:** immutable deployment costs more during the deploy
(double capacity temporarily) but eliminates the risk of a partially
deployed state. For production environments where downtime is costly,
immutable is the default recommendation.

## Expert heuristic: .ebextensions for infrastructure as code (from SKILL.md)

.ebextensions allow you to manage AWS resources as part of the
Beanstalk deployment. This is powerful but ordering-dependent.

```text
.ebextensions/ directory structure (lexicographic ordering):
  .ebextensions/
    ├── 01-options.config      (namespace options, env vars)
    ├── 02-rds.config          (create RDS instance via CloudFormation)
    ├── 03-dynamodb.config     (create DynamoDB table)
    └── 05-hooks.config        (post-deployment hooks)

Each .config file supports:
  option_settings:    (Beanstalk namespace options)
  Resources:          (CloudFormation resources created on deploy)
  files:              (files written to EC2 instances)
  commands:           (commands run BEFORE app deployment)
  container_commands: (commands run DURING app deployment, app dir is CWD)
```

**Key implication:** .ebextensions are the Beanstalk-native way to do
IaC without a separate Terraform/CloudFormation pipeline. But the
resources created in .ebextensions are managed by Beanstalk's internal
CloudFormation stack — deleting the environment deletes those resources
unless `DeletionPolicy: Retain` is set.

## Expert heuristic: CNAME swap for blue-green (from SKILL.md)

CNAME swap is the Beanstalk-native blue-green mechanism. Two
environments (green and blue) are deployed with different CNAME
prefixes. The swap exchanges CNAMEs atomically.

```text
Blue-green CNAME swap flow:
  1. Blue env: myapp-blue.elasticbeanstalk.com (ACTIVE, serving traffic)
  2. Deploy green env: myapp-green.elasticbeanstalk.com (new version)
  3. Wait for green to reach "Ready" + "Green" health
  4. Swap CNAMEs (atomic DNS cutover):
     aws elasticbeanstalk swap-environment-cnames \
       --source-environment-id <blue-id> \
       --destination-environment-id <green-id>
  5. Traffic routes to green (new version). Blue is standby.
  6. Verify green. If rollback needed, swap CNAMEs back.
  7. Terminate blue after monitoring period.

Key: the swap is atomic at the DNS level. But DNS TTL means some
clients hit the old environment for up to 60 seconds after the swap.
```

**Key implication:** CNAME swap is simpler than URL swaps or Route 53
weighted routing for Beanstalk blue-green. The swap is reversible
(swap back to roll back). Always keep the old environment alive until
the monitoring period passes.

## Expert heuristic: .ebextensions YAML syntax gotchas (from SKILL.md)

A baseline model assumes .ebextensions are straightforward YAML. The
expert knows that leading whitespace and YAML parser strictness are
the #1 cause of silent deployment failures.

```text
Common .ebextensions YAML gotchas:
  ├── Leading whitespace: Beanstalk's YAML parser is stricter than
  │     most YAML libraries. A single space before a top-level key
  │     (e.g., "  option_settings:" instead of "option_settings:")
  │     causes the entire config file to be silently skipped.
  │     No error, no warning — the resources/options simply don't apply.
  ├── option_settings list vs map syntax:
  │     AL2023 requires the LIST-of-objects syntax:
  │       option_settings:
  │         - namespace: ...
  │           option_name: ...
  │           value: ...
  │     The older MAP syntax (key-value pairs) is silently ignored
  │     on AL2023 but worked on AL2.
  ├── Tabs are NEVER valid YAML indentation. Copy-pasting from
  │     documentation that uses tabs causes silent parse failures.
  └── CloudFormation Resources block must use exact CFN types —
        a typo like "AWS::S3::Buckett" fails the deployment but
        the error message points at CloudFormation, not the typo.

Expert rule:
  1. Validate every .config file with `yamllint` before deploying
  2. Check Beanstalk events after EVERY deploy — silent skips show
     as "info: No options were updated" for the config file
  3. Use `eb config` to verify the options were actually applied
```

**Key implication:** A syntactically valid YAML file that Beanstalk
silently ignores is worse than a syntax error — it gives false
confidence that configuration was applied. Always verify via
`describe-configuration-settings` after deployment.

## Expert heuristic: worker tier SQS visibility timeout auto-configuration (from SKILL.md)

A baseline model configures the SQS queue visibility timeout on the
queue itself. The expert knows Beanstalk worker tiers have a
non-obvious auto-configuration behavior that overrides it.

```text
Worker tier SQS visibility timeout:
  ├── Beanstalk sets the queue's VisibilityTimeout to MATCH the
  │     environment's HTTP timeout (default 60s)
  ├── If you set a custom timeout on the SQS queue directly,
  │     Beanstalk OVERWRITES it on the next environment update
  ├── To control visibility timeout, set the Beanstalk namespace:
  │     aws:elasticbeanstalk:sqsd:VisibilityTimeout
  └── The SQS daemon also sets maxReceiveCount automatically based
        on the dead-letter queue configuration

Expert rules:
  1. NEVER set visibility timeout on the SQS queue directly —
     Beanstalk will overwrite it
  2. Set it via the sqsd namespace option:
     Namespace=aws:elasticbeanstalk:sqsd,OptionName=VisibilityTimeout
  3. Set the HTTP timeout to be LESS than visibility timeout:
     aws:elasticbeanstalk:application:Environment → HTTP_TIMEOUT
     If HTTP timeout > visibility timeout, the daemon processes
     a message while SQS has already made it visible again →
     duplicate processing
  4. The daemon retries up to maxReceiveCount then sends to DLQ
     — configure the DLQ BEFORE the worker environment starts
```

**Key implication:** The visibility timeout must be coordinated
between Beanstalk's sqsd namespace and the HTTP timeout. Mismatches
cause either duplicate processing (timeout too short) or zombie
messages (timeout too long with no retry).

## Expert heuristic: .platform/hooks vs .ebextensions ordering (from SKILL.md)

AL2023 introduced `.platform/hooks/` alongside `.ebextensions/`. A
baseline model assumes they run at the same time. The expert knows
the execution order determines whether resource references work.

```text
Execution order on AL2023 (critical sequence):
  Phase 1: .ebextensions processing
    ├── 01-setup.config → 02-storage.config → ... (lexicographic)
    │   Each file runs in order:
    │     1. commands         (root, pre-deployment)
    │     2. CloudFormation Resources (if any)
    │     3. files
    │
  Phase 2: Application deployment
    ├── Source bundle extracted to /var/app/current/
    ├── container_commands run (leader_only gate applies)
    │
  Phase 3: .platform/hooks/ execution
    ├── prebuild/   hooks (during build, before deployment)
    ├── predeploy/  hooks (after container_commands, before app start)
    └── postdeploy/ hooks (after app is running and accepting traffic)

Key ordering constraint:
  .ebextensions commands run BEFORE .platform/hooks
  → a file created in .ebextensions/commands IS available to
    .platform/hooks/prebuild/
  → a resource created in .ebextensions/Resources IS available to
    .platform/hooks/postdeploy/
  → BUT .platform/hooks/predeploy/ runs DURING container_commands
    phase — race condition if both modify the same file
```

**Key implication:** `.platform/hooks/` is the AL2023-native
replacement for `.ebextensions/` container commands, but they
co-exist with a specific phase ordering. Use `.ebextensions/` for
infrastructure (CloudFormation resources, packages) and
`.platform/hooks/` for application lifecycle (migrations, cache
warming, smoke tests). Never split related logic across both —
the ordering interaction is a source of silent failures.

## Recent AWS features 2023-2026 (from SKILL.md § Step 15)

**Recent AWS features (2023-2026):**

- **Amazon Linux 2023 platform GA (2023-2024):** All Beanstalk platform
  branches now default to AL2023. AL2 branches are in deprecation.
  AL2023 brings faster boot times, deterministic package updates via
  DNF, and improved security posture.

- **Platform hooks `.platform/hooks/` (2023-2024):** The `.platform/`
  directory replaces `.ebextensions/hooks/` for deployment lifecycle
  hooks on AL2023. Hooks are organized by phase (prebuild, predeploy,
  postdeploy) and support executable scripts.

- **Traffic splitting deployment GA (2023-2024):** Traffic splitting
  is now generally available for all ALB-based environments.
  Configurable canary percentage and evaluation period with automatic
  rollback on health check failure.

- **Enhanced health with AL2023 metrics (2023-2024):** AL2023
  environments report additional health metrics including per-instance
  memory utilization and disk I/O, visible in the Beanstalk health
  dashboard and CloudWatch.

- **Graviton-based instance support (2024-2025):** Beanstalk
  environments on AL2023 support Graviton (arm64) instance types.
  Specify `arm64` architecture in the solution stack for cost-optimized
  compute (up to 20% price/performance improvement).

- **Environment cancellation API (2024-2025):** Long-running
  environment updates can be cancelled via `AbortEnvironmentUpdate`.
