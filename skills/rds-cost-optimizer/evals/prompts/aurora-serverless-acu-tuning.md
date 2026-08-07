# Eval prompt: aurora-serverless-acu-tuning

Optimise the Aurora Serverless v2 cluster configuration for cost. Walk the
seven-dimension analysis and emit the standard optimisation block (TARGET,
VERDICT, REASON, RECOMMENDATION, ESTIMATED_SAVINGS, MIGRATION_STEPS).

DBClusterIdentifier: aurora-serverless-acu-tuning
Engine: aurora-postgresql (Aurora PostgreSQL 15.3)
Region: us-east-1
ServerlessV2ScalingConfiguration:
  MinCapacity: 8.0 ACU
  MaxCapacity: 64.0 ACU

CloudWatch metrics (last 30 days):
  - ACUUtilization: avg=4.2, max=12, min=4.0
  - CPUUtilization: avg=18%, max=50%
  - FreeableMemory: high (workload using ~25% of provisioned)
  - DatabaseConnections: avg=40, max=80

Performance Insights:
  - DBLoad: avg=1, max=4 (low)

Workload context: internal analytics database with variable load.
Peak during business hours (9am-5pm), near-idle overnight and weekends.
Genuine scale-down pattern exists.
