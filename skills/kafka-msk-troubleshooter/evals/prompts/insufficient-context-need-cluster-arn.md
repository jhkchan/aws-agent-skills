# Eval prompt: insufficient-context-need-cluster-arn

Diagnose the following Amazon MSK cluster issue. Emit the standard
VERDICT block.

## Scenario

A user reports: "our Kafka on AWS is having problems." They mention the
region is us-east-1 but provide no further information.

## What the user provided

- Region: us-east-1
- Report: "Kafka is having problems"

## What the user did NOT provide

- Cluster ARN or cluster name
- Cluster type (provisioned / serverless / Cluster Tier Express)
- Observed cluster State
- Error messages from kafka-topics, kafka-consumer-groups, or client logs
- CloudWatch metric snapshots
- Which clients are affected (producers, consumers, both)
