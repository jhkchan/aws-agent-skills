# Eval prompt: auth-failed-iam-token-expiry

Diagnose the connectivity failure for the following RDS DB instance. Walk
the diagnostic tree and emit the standard diagnostic block (TARGET,
VERDICT, REASON, LAYER, EVIDENCE, REMEDIATION).

Symptom: application uses IAM database auth against
db-auth-iam-token-expiry. The first ~50 connections each morning succeed;
subsequent new connections fail with `FATAL: password authentication
failed for user 'iam_app_role'`. The PostgreSQL engine log shows no
password change. Restarting the application temporarily resolves the
issue (next ~50 connections succeed).

DBInstanceIdentifier: db-auth-iam-token-expiry
Engine: postgres
DBInstanceStatus: available
IAMDatabaseAuthenticationEnabled: true
Endpoint: db-auth-iam-token-expiry.cid.on.aws:5432
VpcSecurityGroups: [{VpcSecurityGroupId: sg-rds-prod, Status: active}]
Security group sg-rds-prod inbound rules:
  - tcp/5432 from sg-app (active)

Application context:
  - Java/HikariCP connection pool, maxLifetime=30 minutes.
  - IAM auth: token generated once at pool init, cached and reused for
    new connections in the pool.
  - `aws rds generate-db-auth-token` succeeds when run manually from the
    app-server; connecting with the freshly generated token works.
