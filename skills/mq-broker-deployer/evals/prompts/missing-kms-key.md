# Eval: missing-kms-key

**Difficulty:** easy
**Branch:** PREREQUISITES_MISSING — KMS key alias/does-not-exist-yet not found; encryption requires a valid CMK

## Prompt

Create a production Amazon MQ RabbitMQ broker "prod-rmq2" in
us-east-1. Cluster mode. mq.m5.xlarge. IAM auth. Encryption with
CMK alias/does-not-exist-yet. TLS. AMQP protocol. Subnets
subnet-aaa, subnet-bbb, subnet-ccc in 3 AZs. Security group
sg-rmq999. Tags: Environment=production.
