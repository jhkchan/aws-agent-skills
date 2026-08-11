# Eval: missing-vpc-and-subnet

**Difficulty:** easy
**Branch:** PREREQUISITES_MISSING — VPC/subnet (active/standby requires multi-AZ), security group (broker ports inbound), LDAP directory, and configuration all unspecified

## Prompt

Help me create a new Amazon MQ ActiveMQ broker called "orders-mq" in
us-east-1. I want active/standby with failover and LDAP auth. We will
send order events — should be pretty simple. Region: us-east-1,
Account: 123456789012.
