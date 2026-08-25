# Advanced Patterns — s3-table-bucket-deployer

Moved verbatim from SKILL.md (progressive disclosure; load on demand). Sections keep their original headings.

## Mindset

**One-line takeaway:** An S3 table bucket is a purpose-built container
for Apache Iceberg tables — NOT a general-purpose S3 bucket. You cannot
store arbitrary objects in it. Namespaces must exist before tables.
Table bucket policy is a SEPARATE policy type from the regular S3 bucket
policy. Athena reads S3 Tables via the Iceberg REST catalog endpoint,
not via direct S3 paths. Maintenance (compaction, snapshot management,
unreferenced file cleanup) is enabled by default and configurable.

Three misconceptions dominate S3 Tables misdesign at provisioning time:

- **"A table bucket is just a regular S3 bucket with a different name."**
  It is NOT. A table bucket is a distinct resource type optimized for
  tabular data. You cannot use standard S3 APIs (PutObject, GetObject,
  ListObjects) on it. Table buckets use the `s3tables` API namespace,
  not the `s3` namespace. Regular S3 bucket policies do NOT apply —
  table buckets have their own policy type via
  `put-table-bucket-policy`.

- **"I can create a table directly in a table bucket without a
  namespace."** You CANNOT. The hierarchy is: table bucket → namespace
  → table. A namespace must exist before any table can be created in
  it. This is a hard API dependency — `create-table` fails if the
  namespace does not exist.

- **"Athena can query S3 Tables by pointing at the S3 bucket path."**
  It CANNOT. Athena accesses S3 Tables through the Apache Iceberg REST
  catalog endpoint, not by specifying an S3 path. The REST catalog
  provides the table metadata that Athena needs to read Iceberg data
  files. Lake Formation governs access to these tables for fine-grained
  permission control.

---

## Expert heuristic: maintenance automation is on by default

S3 Tables provides three automatic maintenance types for every Iceberg
table, all ENABLED by default: **compaction** (merges small files into
larger ones, ~512 MB target), **snapshot management** (expires old
snapshots, controls metadata growth), and **unreferenced file cleanup**
(removes orphaned data files, reclaims storage). All are per-table
configurable. Unlike self-managed Iceberg on S3, you do NOT need to
build or operate separate compaction jobs. The decision is whether to
keep defaults or tune settings per workload. Disabling is possible but
almost always wrong for production.

---

## Expert heuristic: Athena reads via REST catalog, not S3 paths

A baseline model points Athena at the S3 bucket path. Athena actually
accesses S3 Tables through the Apache Iceberg REST catalog endpoint:
S3 Table Bucket provisions the REST catalog, the Athena workgroup
references it, Lake Formation grants permissions to the query role,
and queries use `namespace.table` notation. Without the REST catalog,
Athena returns "table not found." The S3 path is irrelevant.

---

## Step 10 — Recent features

**Recent AWS features (2024-2026):**

- **S3 Tables general availability (2024-2025):** Amazon S3 Tables
  launched as purpose-built storage for tabular data using Apache
  Iceberg, with built-in maintenance and REST catalog integration.

- **Iceberg REST catalog for Athena (2024-2025):** Athena integration
  via the REST catalog endpoint, enabling SQL queries with time travel,
  schema evolution, and ACID support.

- **Lake Formation fine-grained access for S3 Tables (2024-2025):**
  Lake Formation integration for table-level and column-level
  permissions on S3 Tables resources, enabling centralized access
  governance.

- **Iceberg v2 row-level operations (2024-2025):** S3 Tables supports
  Iceberg v2 format with UPDATE, DELETE, and MERGE INTO operations
  for row-level mutations.

- **Cross-account table bucket policy (2024-2025):** Table bucket
  policies support cross-account access for sharing tables with other
  AWS accounts.

- **Terraform provider support (2024-2025):** The Terraform AWS
  provider added `aws_s3tables_table_bucket`,
  `aws_s3tables_namespace`, and `aws_s3tables_table` resources for
  infrastructure-as-code provisioning of S3 Tables.
