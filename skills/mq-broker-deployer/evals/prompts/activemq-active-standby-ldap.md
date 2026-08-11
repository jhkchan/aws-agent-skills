# Eval: activemq-active-standby-ldap

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — ActiveMQ active/standby (2 AZs), LDAP auth, CMK encryption, CloudWatch alarms for CpuUtilization/MemoryUtilization/EnqueueCount, maintenance window

## Prompt

Create a production Amazon MQ ActiveMQ broker "prod-mq" in
us-east-1. Active/standby HA. mq.m5.large. LDAP auth against
Managed AD d-1234567890. CMK alias/prod-mq-kms. TLS. OpenWire +
AMQP protocols. CloudWatch alarms for CpuUtilization >80%,
MemoryUtilization >80%, EnqueueCount anomaly. Subnets subnet-aaa
and subnet-bbb in 2 AZs. Security group sg-mq123 inbound 61617,
5671, 8162 from sg-app456. Auto minor version upgrade. Maintenance
window SUN 03:00 UTC. Tags: Environment=production.
