# Eval: activemq-stomp-mqtt-protocols

**Difficulty:** medium
**Branch:** READY_TO_DEPLOY — ActiveMQ dev broker with single instance mode, full protocol surface (OpenWire, STOMP, MQTT, AMQP, WS), basic auth, AWS-managed KMS

## Prompt

Provision an Amazon MQ ActiveMQ broker named "dev-mq-multi" in
us-east-1 for a dev environment. This broker needs the full
multi-protocol surface: OpenWire (61617), STOMP (61614), MQTT (8883),
AMQP (5671), and WebSocket WSS (61619). Single instance mode (dev only,
no HA needed). Use mq.t3.micro. Username/password authentication
(basic). AWS-managed KMS key for encryption at rest (dev, no CMK
needed). Enable general logs. Subnet group dev-mq-subnet in us-east-1a.
Security group sg-dev-mq inbound 61617, 61614, 8883, 5671, 61619, 8162
from sg-dev-app. Tags: Environment=dev, Workload=messaging. Account ID:
123456789012.
