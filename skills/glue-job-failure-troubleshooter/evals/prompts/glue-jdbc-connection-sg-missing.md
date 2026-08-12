# Eval prompt: glue-jdbc-connection-sg-missing

Diagnose the AWS Glue job failure for the following job. Walk the
symptom-driven diagnostic tree and emit the standard diagnostic block
(TARGET, VERDICT, REASON, LAYER, EVIDENCE, REMEDIATION).

Symptom: Glue job `etl-from-rds` fails with
`org.postgresql.util.PSQLException: Connection timed out` when trying
to read from RDS PostgreSQL. The Glue JDBC connection exists; the
JDBC URL is correct; the RDS instance is in the same VPC.

```text
JobName: glue-jdbc-connection-sg-missing
JobRunId: jr_ghi789
WorkerType: G.2X
NumberOfWorkers: 5
GlueVersion: glue-4.0

Glue connection: rds-prod-connection
  ConnectionType: jdbc
  ConnectionProperties.JDBC_URL: jdbc:postgresql://
    rds-prod.cluster-xxx.us-east-1.rds.amazonaws.com:5432/db
  PhysicalConnectionRequirements:
    SubnetId: subnet-private-a
    SecurityGroupIdList: [sg-glue-etl]
    AvailabilityZone: us-east-1a

RDS instance:
  DBInstanceIdentifier: rds-prod
  VpcSecurityGroups: [sg-rds-prod]
  Port: 5432

sg-rds-prod inbound rules:
  - Port 5432, Source: sg-bastion (bastion host)
  - (NO rule for sg-glue-etl)

sg-glue-etl outbound: 0.0.0.0/0 all ports (allow all)

Subnet route table: subnet-private-a can reach the RDS subnet
  (same VPC, local route).
```

JDBC connections need a Glue connection AND a security group. The
database's security group must allow inbound from the Glue connection's
security group on the database port. Verify the SG configuration and
recommend the fix.
