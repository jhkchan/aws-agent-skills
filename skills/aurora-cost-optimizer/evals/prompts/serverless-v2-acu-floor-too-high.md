# Eval prompt: serverless-v2-acu-floor-too-high

Optimise the Aurora cluster cost. Walk the seven-dimension optimisation
logic and emit the standard optimisation block (TARGET, VERDICT,
REASON, RECOMMENDATION, ESTIMATED_SAVINGS, MIGRATION_STEPS).

Cluster: reporting-serverless (case serverless-v2-acu-floor-too-high)
Engine: aurora-postgresql (15)
Region: us-east-1
ServerlessV2ScalingConfiguration:
  MinCapacity: 8
  MaxCapacity: 32
CloudWatch (last 30 days):
  - CPUUtilization: avg=8%, max=22%
  - ServerlessDatabaseCapacity: avg=4.5, peak=14
Cost Explorer:
  - Aurora:ServerlessUsage: ~$700/month (consistent with MinCapacity=8
    floor dominating)
Workload: internal BI dashboard with spiky daytime load; idle
overnight; no sub-second latency SLA.
