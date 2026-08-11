# Eval: rabbitmq-cluster-iam-auth

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — RabbitMQ cluster (3 AZs), IAM auth via authenticationStrategy=LDAP, 3 subnets, quorum queues for HA

## Prompt

Create a production Amazon MQ RabbitMQ broker "prod-rmq" in
us-east-1. Cluster mode (3 brokers). mq.m5.large. IAM
authentication. CMK alias/prod-rmq-kms. TLS. AMQP + STOMP
protocols. Quorum queues for HA. Subnets subnet-aaa, subnet-bbb,
subnet-ccc in 3 AZs. Security group sg-rmq456 inbound 5671, 61614.
CloudWatch alarms for CpuUtilization and QueueSize. Tags:
Environment=production, Engine=rabbitmq.
