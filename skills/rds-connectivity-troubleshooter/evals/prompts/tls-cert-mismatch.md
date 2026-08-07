# Eval prompt: tls-cert-mismatch

Diagnose the connectivity failure for the following RDS DB instance. Walk
the diagnostic tree and emit the standard diagnostic block (TARGET,
VERDICT, REASON, LAYER, EVIDENCE, REMEDIATION).

Symptom: Java application cannot connect to db-tls-cert-mismatch after a
recent maintenance window. The error from the JDBC driver is
`unable to get local issuer certificate`. Before the maintenance window,
connections worked. During the window, the instance's CA was rotated
from `rds-ca-2019` to `rds-ca-e2024`.

DBInstanceIdentifier: db-tls-cert-mismatch
Engine: mysql
DBInstanceStatus: available
Endpoint: db-tls-cert-mismatch.cid.on.aws:3306
CACertificateIdentifier: rds-ca-e2024
VpcSecurityGroups: [{VpcSecurityGroupId: sg-rds-prod, Status: active}]
Security group sg-rds-prod inbound rules:
  - tcp/3306 from sg-app (active)
Parameter group: require_secure_transport = 1

Client context:
  - Java 17 application using mysql-connector-j.
  - Client truststore contains rds-ca-2019 only.
  - `nc -vz db-tls-cert-mismatch.cid.on.aws 3306` succeeds.
  - Connecting with `mysql --ssl-mode=REQUIRED` from the same host also
    fails with the same error.
