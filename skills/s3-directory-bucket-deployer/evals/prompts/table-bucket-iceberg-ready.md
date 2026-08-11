# Eval prompt: table-bucket-iceberg-ready

Design a deployment plan for an S3 Tables table bucket for Apache
Iceberg analytics. Emit the standard VERDICT block
(DIRECTORY_BUCKET_SPEC, VERDICT, CHECKLIST, VERIFICATION_COMMANDS).

Requirements:

- Table bucket name: events-iceberg-tables
- AZ: us-east-1a (resolve to AZ ID)
- Region: us-east-1
- Format: Apache Iceberg
- Compute: EMR Spark cluster in use1-az1 (subnet subnet-aaa)
- Query engines: Athena + Spark
- No CRR, no versioning, no Object Lock needed
- Account: 111111111111

Additional context: the analytics team is building an event analytics
platform on Apache Iceberg tables stored in S3 Tables. The table
bucket must be in the same AZ as the EMR Spark cluster for optimal
query performance. Athena will also query the Iceberg tables via
standard Iceberg catalog integration. The workload is tabular analytics
(not object-level reads/writes).
