# Error Handling — Glue Crawler Deployer

Error-handling deep dives moved verbatim from SKILL.md (progressive disclosure — load on demand).

## Crawler failure modes and fixes

### Crawler fails with AccessDeniedException
- IAM role missing S3 permissions on the data source, or Lake
  Formation permissions on the database. Verify the role has
  `s3:GetObject`, `s3:ListBucket` on the bucket, and LF grants on the
  database.

### Crawler creates wrong schema (all string columns)
- No custom classifier matched. A built-in classifier guessed all
  fields as string. Create a custom classifier for your data format
  and list it BEFORE built-in classifiers.

### Partitions not discovered
- Folder structure does not match `key=value` format. The crawler
  expects `year=2026/month=08/day=05/`. Verify the folder naming. Or
  use partition projection if the range is predictable.

### JDBC crawler cannot connect
- Glue Connection has wrong VPC/subnet/SG. The connection must be in
  the same network as the database. Test the connection:
  `aws glue test-connection --connection-name <name>`.

### Crawler runs but no tables created
- TableThreshold too high, or the S3 path is empty. Check if data
  files exist at the configured path. Lower TableThreshold if needed.

