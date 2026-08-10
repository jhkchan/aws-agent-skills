# Eval prompt: jdbc-connection-missing-security-group

Diagnose the Glue job failure. Walk the seven-category diagnostic tree
and emit the standard diagnostic block (TARGET, VERDICT, REASON,
CATEGORY, EVIDENCE, REMEDIATION).

JobName: orders-etl-job (case jdbc-connection-missing-security-group)
RunId: jr_def789abc012
Region: us-east-1
GlueVersion: 4.0
WorkerType: G.1X
NumberOfWorkers: 3

get-job-run output:
  State: FAILED
  ExecutionTime: 18
  ErrorMessage: "VPC Connection error: Failed to connect"

Glue connection nightly-rds-conn:
  SUBNET_ID: subnet-glue-private-1a
  SECURITY_GROUP_ID: sg-glue123
  JDBC URL: jdbc:postgresql://orders-db.cluster-abc.us-east-1.rds.amazonaws.com:5432/orders

Database SG (sg-rds456) inbound rules:
  - port 5432, source 10.0.0.0/8 (corporate VPN)
  (NO rule for sg-glue123 on 5432)

Glue SG (sg-glue123) egress rules:
  - 0.0.0.0/0 all ports (default)

Route table for subnet-glue-private-1a:
  - routes to DB subnet via VPC peering (OK)

Last successful run: 3 days ago.
