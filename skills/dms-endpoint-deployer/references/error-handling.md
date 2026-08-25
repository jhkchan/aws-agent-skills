# DMS Endpoint Deployer — error handling (moved from SKILL.md)

Loaded on demand — content moved verbatim from SKILL.md (progressive disclosure; nothing deleted).

## Error handling (moved from SKILL.md)


### Connection test fails with timeout
- Verify the replication instance is in the same VPC and subnet group
  as the source/target database. Check security group rules allow
  inbound from the replication instance on the database port.

### CDC task fails with "could not create replication slot"
- PostgreSQL: verify `wal_level=logical` and `max_replication_slots >
  0`. Check for conflicting slot names. Verify the DMS user has
  `REPLICATION` privilege.

### CDC task misses UPDATE/DELETE operations (Oracle)
- Supplemental logging is not enabled. Run `ALTER DATABASE ADD
  SUPPLEMENTAL LOG DATA` and `ALTER TABLE ... ADD SUPPLEMENTAL LOG
  DATA (ALL) COLUMNS` for all replicated tables.

### SSL handshake fails
- For `verify-ca` / `verify-full`, verify the certificate is imported
  and not expired. Check that the certificate ARN in the endpoint
  matches the imported certificate.

### Secrets Manager credential retrieval fails
- Verify the DMS service role has `secretsmanager:GetSecretValue` on
  the secret. Check the secret's JSON payload includes `username` and
  `password` fields. If the secret was recently rotated, re-test the
  endpoint connection.

