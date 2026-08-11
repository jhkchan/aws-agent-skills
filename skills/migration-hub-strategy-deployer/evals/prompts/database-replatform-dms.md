# Eval prompt: database-replatform-dms

Design a migration assessment for a portfolio that includes a database
replatform from Oracle 11g to Aurora PostgreSQL. Emit the standard
ASSESSMENT block including the DMS handoff plan.

Design reference: database-replatform-dms
Account: 111111111111
Home region: us-east-1

Portfolio: 20 servers, one Oracle 11g database (srv-db01).
Discovery: agent-based, 14-day collection.
Strategy: replatform (Oracle 11g -> Aurora PostgreSQL).
DMS replication instance: dms.r5.xlarge provisioned.
AWS SCT: not yet run.
Source endpoint: oracle-prod.example.com:1521.
Target endpoint: aurora-pg.cluster-xxxxx.us-east-1.rds.amazonaws.com:5432.
