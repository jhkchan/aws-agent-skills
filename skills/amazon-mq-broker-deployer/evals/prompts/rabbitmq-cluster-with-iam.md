# Eval: rabbitmq-cluster-with-iam

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — RabbitMQ cluster mode with 3 nodes, IAM authentication (creation-time-only), customer CMK + TLS + audit logging

## Prompt

Provision a production Amazon MQ RabbitMQ broker named "prod-rabbit" in
us-east-1. We need cluster mode with 3 nodes for horizontal scaling and
quorum-based HA. Workload is high-throughput AMQP 0-9-1 at ~5,000
connections and ~15,000 msg/sec. Use mq.m5.2xlarge instance type per
node. AWS IAM authentication (passwordless, AWS-native). Customer-
managed CMK alias/rabbit-kms for encryption at rest. TLS enabled.
Enable CloudWatch general and audit logs. Protocols: AMQP (5671),
RabbitMQ Management (15671). Subnet group prod-rabbit-subnet spans 3
AZs. Security group sg-rabbit inbound 5671, 15671 from sg-app.
Automatic minor version upgrades enabled. Tags: Environment=production,
Workload=messaging. Account ID: 123456789012.
