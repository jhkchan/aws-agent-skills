# Advanced Patterns — Kinesis Data Analytics Deployer

Edge-case handling and recent AWS features moved verbatim from SKILL.md for progressive disclosure. Load on demand.

## Recent AWS features (2024-2026) (moved from SKILL.md)

- **Studio notebooks with Zeppelin (2024-2026):** interactive Apache
  Zeppelin notebooks connected to live Kinesis streams. Provides
  exploratory Flink/SQL analysis without deploying a full application.
  Notebooks can be promoted to production STREAMING applications.
- **Session windows SQL (2024-2026):** native `SESSION()` window
  function in KDA SQL for sessionization use cases (user sessions
  with inactivity gaps). Replaces workarounds using hopping windows.
- **Application snapshots (2024-2026):** user-triggered snapshots of
  application state for planned stop/start, code updates with state
  preservation, and blue/green deployments.
- **Custom application code via S3 (2024-2026):** Flink applications
  can load custom JARs/Python packages from S3 with versioned keys
  for reproducible deployments.
- **Flink 1.19 runtime (2025-2026):** FLINK-1_19 runtime with
  adaptive batch scheduling, improved connector lifecycle, and Python
  UDF performance improvements. Use the latest stable runtime.
- **Glue Data Catalog integration (2024-2026):** Studio notebooks and
  Flink apps can read table schemas directly from the Glue Data
  Catalog via `CatalogConfiguration`.
- **VPC support for private sources (2024-2026):** KDA applications
  can connect to private MSK, private OpenSearch, and private RDS via
  VPC subnets and security groups.
- **Schema Registry for Avro/Protobuf (2024-2025):** AWS Glue Schema
  Registry integration for type-safe stream deserialization. The
  execution role needs `glue:GetSchemaVersion`.

## Edge-case handling (moved from SKILL.md)

- **Cross-account Kinesis source:** the execution role needs
  `kinesis:GetRecords` on the cross-account stream AND the stream
  policy in the other account must grant your execution role. KDA
  does NOT support cross-account role assumption within an application.
- **Schema evolution (Avro/Protobuf):** when the source schema changes,
  update the Glue Schema Registry with a backward-compatible version.
  KDA Flink apps automatically use the latest schema version. NEVER
  make breaking schema changes without an application update.
- **Snapshot restore with code changes:** if the new code removed a
  Flink operator, restore fails with `AllowNonRestoredState: false`.
  Set `AllowNonRestoredState: true` only during verified breaking
  changes — otherwise you silently drop state.
- **VPC source (private MSK):** KDA applications can connect to
  private MSK via VPC configuration. The execution role needs
  `ec2:CreateNetworkInterface`,
  `ec2:DescribeNetworkInterfaces`, and `ec2:DeleteNetworkInterface`.
- **Firehose source with transformation:** Firehose can apply Lambda
  transformation before KDA reads. The KDA app sees the transformed
  record. Ensure the transformation is idempotent — KDA may replay
  records on failure.
- **SQL app with multiple inputs:** SQL apps can read from multiple
  Kinesis streams via multiple `Inputs` entries. Each input needs its
  own schema and `NamePrefix`. JOINs across streams require aligned
  event-time watermarks.
- **Studio notebook to production:** when promoting a Zeppelin
  notebook to a STREAMING application, the notebook's paragraphs are
  compiled into a Flink JAR. Test the promoted app separately —
  notebook behavior may differ in a deployed context (e.g., parallel
  paragraph execution).
- **Parallelism change with state:** increasing `Parallelism` requires
  a snapshot restore — Flink redistributes operator state across the
  new subtasks. NEVER change parallelism without a snapshot if the app
  is stateful.

