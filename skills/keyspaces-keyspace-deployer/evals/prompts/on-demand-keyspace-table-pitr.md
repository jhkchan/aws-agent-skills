# Eval: on-demand-keyspace-table-pitr

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — on-demand keyspace+table, PITR explicitly enabled, CMK encryption, VPC endpoint with private DNS, composite partition key (user_id + event_date)

## Prompt

Create an Amazon Keyspaces keyspace called event_store in
us-east-1. Create a table user_events with columns: user_id
(uuid), event_date (date), event_time (timestamp), event_type
(text), payload (blob). Partition key: (user_id, event_date).
Clustering key: event_time DESC. Use on-demand capacity. Enable
point-in-time recovery. Use KMS CMK alias/keyspaces-cmk for
encryption at rest. Create a VPC endpoint in VPC vpc-aaa11122,
subnets subnet-aaa111 and subnet-bbb222, security group
sg-keyspaces-client. Tags: Environment=production,
Team=data-platform.
