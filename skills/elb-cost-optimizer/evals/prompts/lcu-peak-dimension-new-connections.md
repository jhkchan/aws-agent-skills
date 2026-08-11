# Eval prompt: lcu-peak-dimension-new-connections

Optimise the following ALB for cost. Walk all optimization dimensions
and emit the standard optimization block (TARGET, VERDICT, REASON,
RECOMMENDATION, ESTIMATED_SAVINGS, ACTION_STEPS).

## Scenario

An ALB named `web-frontend-prod` serves a high-traffic web application.
The LCU bill is higher than expected.

## Known facts

- ALB name: `web-frontend-prod`
- Region: us-east-1
- Listeners: 1 x HTTPS:443 (1 listener rule besides the default)
- Target group: 10 x EC2 instances (t3.xlarge, nginx)
- 14-day CloudWatch LCU metrics:
  - ConsumedLCUs: average 18.0, max 25.0
  - Per-dimension breakdown (hourly average):
    - NewConnectionCount: 500/sec -> 500/25 = 20.0 LCU
    - ActiveConnectionCount: 12,000 -> 12000/3000 = 4.0 LCU
    - ProcessedBytes: 1.5 GB/hour -> 1.5/1 = 1.5 LCU
    - RuleEvaluations: 2000/sec -> 2000/1000 = 2.0 LCU
  - Peak dimension: **new connections at 20.0 LCU**
- Cost Explorer: $121.54/month in LCU charges ($0.008 x 18.0 avg
  LCU x 730h) + $16.43/month base = $137.97/month total
- HTTP keep-alive is DISABLED on the nginx targets (responses send
  `Connection: close`). Each client request opens a new TCP+TLS
  connection to the ALB.
- The application serves a REST API with frequent short-lived requests
  from mobile clients

## Symptom

The LCU cost is high. The team suspects the new connection rate is the
bottleneck but does not know how to reduce it.
