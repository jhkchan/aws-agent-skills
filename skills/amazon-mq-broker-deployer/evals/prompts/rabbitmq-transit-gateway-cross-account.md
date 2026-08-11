# Eval: rabbitmq-transit-gateway-cross-account

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — RabbitMQ active/standby with transit gateway for cross-account (123456789012) message consumption via RAM-shared TGW

## Prompt

Provision an Amazon MQ RabbitMQ broker named "shared-rabbit" in
us-east-1 with active/standby HA. The broker needs cross-account access
via transit gateway tgw-0abc123 — account 123456789012 must consume
messages from a separate VPC. Use mq.m5.large. Username/password auth.
Customer CMK alias/shared-rabbit-kms for encryption at rest. TLS
enabled. CloudWatch general and audit logs. Protocols: AMQP (5671).
Subnet group shared-rabbit-subnet spans 2 AZs. Security group
sg-shared-rabbit inbound 5671 from sg-app and from the peer VPC CIDR
(10.20.0.0/16). Transit gateway tgw-0abc123 shared via RAM to account
123456789012. Tags: Environment=production, Workload=shared-messaging.
Account ID: 123456789012.
