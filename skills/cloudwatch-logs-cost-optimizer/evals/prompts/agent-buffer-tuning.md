# Eval prompt: agent-buffer-tuning

Optimise the following CloudWatch Logs configuration for cost. Walk the
agent buffer tuning decision framework and emit the standard optimization
block (TARGET, VERDICT, REASON, RECOMMENDATION, ESTIMATED_SAVINGS,
MIGRATION_STEPS).

LogGroupName: /ec2/app-logs
RetentionInDays: 14
Region: us-east-1
StoredBytes: 196 GB

Fleet details:
  - Hosts: 100 EC2 instances running CloudWatch agent
  - Agent batch_count: 1000 (default)
  - Agent batch_size: 1048576 (default, 1 MB)
  - Agent batch_wait_time: 5 seconds (default)

Metrics (last 30 days, aggregated across fleet):
  - IncomingBytes avg: 28 GB/day
  - IncomingLogEvents avg: 12,000,000/hour (288M/day)

CloudWatch Logs API metrics:
  - PutLogEvents requests: ~288,000/hour
  - Monthly PutLogEvents: ~208,512,000 (~209M requests/month)

Cost Explorer (last month):
  - Logs ingestion: $420.00 (840 GB × $0.50)
  - Logs storage: $5.88 (196 GB × $0.03)
  - PutLogEvents requests: $83.40 (209M / 1M × $0.40)
  - Total: $509.28/month

Workload context: microservice fleet logs. Events are non-critical
debug+info level. 60-second data-loss window on agent failure is
acceptable (events are also shipped to a downstream aggregator).
