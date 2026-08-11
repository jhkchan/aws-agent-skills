# Eval: missing-vpc-subnet

**Difficulty:** easy
**Branch:** PREREQUISITES_MISSING — no VPC or subnet IDs provided; active/standby requires 2 subnets in 2 AZs

## Prompt

Create an Amazon MQ ActiveMQ broker "prod-mq2" in us-east-1.
Active/standby HA. mq.m5.large. LDAP auth. CMK alias/prod-mq-kms.
TLS. OpenWire protocol. Security group sg-mq999. No subnets or
VPC specified yet — will figure those out later.
