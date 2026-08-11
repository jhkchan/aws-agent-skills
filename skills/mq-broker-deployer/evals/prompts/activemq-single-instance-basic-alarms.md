# Eval: activemq-single-instance-basic-alarms

**Difficulty:** medium
**Branch:** READY_TO_DEPLOY — ActiveMQ single-instance, basic auth, CloudWatch alarms for CpuUtilization/MemoryUtilization/EnqueueCount

## Prompt

Create a small Amazon MQ ActiveMQ broker "dev-mq" in us-east-1.
Single-instance. mq.t3.small. Basic auth (admin user). TLS.
OpenWire protocol on port 61617. Security group sg-devmq789
inbound 61617 from 10.0.0.0/16. Subnet subnet-devaaa. CloudWatch
alarms for CpuUtilization >80%, MemoryUtilization >80%, and
EnqueueCount drop. Tags: Environment=dev.
