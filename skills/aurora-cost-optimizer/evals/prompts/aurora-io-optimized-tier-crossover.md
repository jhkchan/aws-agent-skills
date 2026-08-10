# Eval prompt: aurora-io-optimized-tier-crossover

Optimise the Aurora cluster cost. Walk the seven-dimension optimisation
logic and emit the standard optimisation block (TARGET, VERDICT,
REASON, RECOMMENDATION, ESTIMATED_SAVINGS, MIGRATION_STEPS).

Cluster: orders-prod-io (case aurora-io-optimized-tier-crossover)
Engine: aurora-mysql (8.0)
Region: us-east-1
Storage tier: Standard
Storage used: 1,000 GB
I/O requests (last 30 days): 600,000,000
Cost Explorer (last 30 days):
  - Aurora:StorageUsage: 1,000 GB × $0.10 = $100
  - Aurora:IOUsage: 600M × $0.20 = $120
  - Aurora:InstanceUsage: minimal (this case isolates I/O tier)
