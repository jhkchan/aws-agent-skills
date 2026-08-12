# Eval: aurora-mysql-major-version-upgrade

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — Aurora MySQL Blue/Green, major version upgrade 5.7 to 8.0 in green, parameter group change, green validation, replication active, switchover timeout

## Prompt

Create an RDS Blue/Green Deployment for my Aurora MySQL cluster
prod-mysql-db (aurora-mysql 5.7.mysql_aurora.2.11.0) in
us-east-1, account 123456789012. I want to upgrade to MySQL 8.0
(8.0.mysql_aurora.3.04.0) in the green environment. Use
parameter group prod-mysql80-params for green. I have connection
retry logic in my application. Switchover timeout 300 seconds.
Tags: Environment=production, Upgrade=mysql57-to-80.
