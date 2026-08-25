# EMR Serverless Deployer — advanced patterns (load on demand)

Feature deep dives and edge-case catalogs, moved verbatim from SKILL.md.

## Latest EMR Serverless features (2024-2026) (moved verbatim from SKILL.md lines 479-503)


- **Spark Connect (2024-2026):** remote Spark sessions via thin client
  protocol. Enables interactive data exploration from notebooks and
  IDEs without running a local Spark driver. The driver runs on the
  EMR Serverless cluster.
- **Interactive endpoints (2024-2026):** managed endpoints for Jupyter
  Enterprise Gateway and Spark Connect. Billed per-second while active.
  Pair with auto-stop for cost control.
- **Automated application start/stop (2024-2025):** auto-start when a
  job is submitted; auto-stop after configurable idle timeout. Saves
  cost for non-24/7 workloads.
- **Lake Formation integration (2024-2026):** fine-grained access
  control (column-level, row-level) on Glue tables via Lake Formation.
  The execution role needs `lakeformation:GetDataAccess`.
- **Gang scheduling (2024-2025):** all workers for a job are scheduled
  simultaneously or the job waits. Eliminates partial allocation
  deadlocks for large Spark jobs.
- **Custom images (2024-2025):** custom Docker images from ECR for
  additional libraries (pandas, scikit-learn, custom JARs). Pin the
  image tag — NEVER use `latest`.
- **Blueprints (2024-2026):** reusable application templates for
  common Spark/Hive patterns. Reduces setup time for teams.
- **Application snapshots (2024-2026):** save and restore application
  state (including loaded libraries and initialized JVMs) to reduce
  cold-start time for recurring jobs.

## Edge-case handling catalog (moved verbatim from SKILL.md lines 628-657)


- **Cross-account S3 access:** the execution role needs `s3:GetObject`
  on the cross-account bucket AND the bucket policy in the other
  account must grant your execution role. EMR Serverless does NOT
  support cross-account IAM role assumption within a job.
- **Custom image updates:** when updating a custom image, the
  application must be stopped and restarted to pull the new image.
  Running jobs are NOT interrupted; new jobs use the new image.
- **Pre-initialized capacity with auto-stop:** when auto-stop triggers
  (idle for `idleTimeoutMinutes`), pre-initialized capacity is released.
  A new job re-starts the application and re-initializes workers
  (cold start 60-90s). To avoid this, set auto-stop timeout longer
  than the expected gap between jobs.
- **Lake Formation column-level access:** the execution role needs
  `lakeformation:GetDataAccess` and the Lake Formation admin must
  grant column-level permissions to the role. Without it, the job
  sees all columns (security risk) or none (AccessDenied).
- **Gang scheduling for large jobs:** jobs with > 100 workers may
  partially allocate and deadlock if gang scheduling is disabled.
  Enable gang scheduling via `--configuration-overrides` with
  `spark.scheduler.gang.enabled=true`.
- **Spark Connect session isolation:** each Spark Connect session runs
  in the same application but with isolated SparkContext. Resource
  contention is possible if multiple sessions run heavy queries
  simultaneously. Use separate applications for teams that need
  guaranteed resources.
- **Hive to Spark migration:** HiveQL queries can run on Spark SQL
  with minimal changes. Common gotchas: `CLUSTER BY` (not supported
  in Spark SQL), `TRANSFORM` (different syntax), and SerDe
  differences for custom formats. Test before migrating.
