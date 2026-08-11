# Eval: provisioned-autoscaling

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — provisioned capacity with auto-scaling on read and write, target 70%, min 100 max 5000

## Prompt

Create a table sensor_readings in keyspace telemetry_keyspace.
Columns: sensor_id (text), reading_time (timestamp), value
(double), unit (text). Partition key: sensor_id. Clustering key:
reading_time DESC. Use provisioned capacity with 500 read
capacity units and 1000 write capacity units. Enable auto-scaling
with target 70%, min 100, max 5000 on both read and write. Region
us-east-1. Tags: Environment=production, Workload=iot-telemetry.
