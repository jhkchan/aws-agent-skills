# Eval prompt: timeout-sg-missing-rule

Diagnose the connectivity failure for the following RDS DB instance. Walk
the OSI-aligned diagnostic tree and emit the standard diagnostic block
(TARGET, VERDICT, REASON, LAYER, EVIDENCE, REMEDIATION).

Symptom: application on EC2 instance i-app-server (private IP 10.42.5.10,
subnet subnet-bbb, security group sg-app, AZ us-east-1a) cannot reach
db-timeout-sg-missing-rule. `telnet db-timeout-sg-missing-rule.cid.on.aws 3306`
hangs and returns "Operation timed out" after 10 seconds. No error appears
in the MySQL engine log. Connections from hosts in 10.42.0.0/24 work
normally.

DBInstanceIdentifier: db-timeout-sg-missing-rule
Engine: mysql
DBInstanceStatus: available
Endpoint: db-timeout-sg-missing-rule.cid.on.aws:3306
VpcSecurityGroups: [{VpcSecurityGroupId: sg-rds-prod, Status: active}]
Security group sg-rds-prod inbound rules:
  - tcp/3306 from 10.42.0.0/24
  - tcp/3306 from sg-app-old (a deleted security group)
DBSubnetGroup: prod-db-subnet-group (subnets in us-east-1a, us-east-1b)

Caller context: i-app-server is in subnet-bbb (CIDR 10.42.5.0/24). Its
NACL is the default VPC NACL (allow all). The route table for subnet-bbb
has a local route to the RDS VPC CIDR. The instance's subnet has the
default NACL.
