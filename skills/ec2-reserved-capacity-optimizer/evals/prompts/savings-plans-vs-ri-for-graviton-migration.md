# Eval prompt: savings-plans-vs-ri-for-graviton-migration

Optimise the following EC2 commitment strategy for cost. Walk all
commitment dimensions and emit the standard optimization block (TARGET,
VERDICT, REASON, RECOMMENDATION, ESTIMATED_SAVINGS, ACTION_STEPS).

## Scenario

A fleet of c5.xlarge (x86_64) instances is planning a migration to
c7g.xlarge (Graviton) in 3 months. The team wants to commit for savings
but needs flexibility for the upcoming family migration.

## Known facts

- Current fleet: 25 x c5.xlarge (Linux, x86_64), us-east-1, 24/7
- Planned migration: c5.xlarge -> c7g.xlarge (Graviton) in 3 months
- Current commitment: None (100% on-demand)
- Cost Explorer: $1,752/month on on-demand EC2 ($0.192/h x 730h x 25
  = ~$3,504... actually $0.192 x 730 = $140.16/instance/month x 25 =
  $3,504/month... wait, let me re-check. On-demand c5.xlarge is
  $0.17/h in us-east-1. $0.17 x 730 x 25 = $3,102.50/month.)
- The migration will reduce per-hour cost by ~20% (Graviton
  price-performance advantage)
- The team wants to commit now for savings but cannot lock into the
  c5 family because they are migrating away in 3 months
- On-demand rate for c5.xlarge: $0.17/h (us-east-1, Linux)
- On-demand rate for c7g.xlarge: $0.1415/h (us-east-1, Linux)

## Symptom

The team wants to reduce the on-demand bill immediately but needs a
commitment vehicle that provides flexibility across the upcoming
instance-family migration (c5 -> c7g). Standard RIs cannot cross
families.
