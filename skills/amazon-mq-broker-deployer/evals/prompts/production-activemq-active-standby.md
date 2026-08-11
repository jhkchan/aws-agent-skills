# Eval: production-activemq-active-standby

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — all checklist items verified, active/standby HA + customer CMK + TLS + LDAP auth + OpenWire/STOMP/MQTT protocols + audit logging

## Prompt

Provision a production Amazon MQ ActiveMQ broker named "prod-mq" in
us-east-1. We need active/standby HA (standby in a different AZ).
Workload is JMS-style messaging with OpenWire clients at ~500
connections and ~1,000 msg/sec. Use mq.m5.large instance type. LDAP
authentication against AWS Managed Microsoft AD (d-1234567890).
Customer-managed CMK alias/prod-mq-kms for encryption at rest. TLS
enabled. Enable CloudWatch general and audit logs. Protocols: OpenWire
(61617), STOMP (61614), MQTT (8883), and Web Console (8162). Subnet
group prod-mq-subnet spans 2 AZs (us-east-1a, us-east-1b). Security
group sg-mq123 inbound 61617, 61614, 8883, 8162 from sg-app456.
Automatic minor version upgrades enabled, window SUN 03:00 UTC. Tags:
Environment=production, Workload=messaging. Account ID: 123456789012.
