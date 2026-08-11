# Eval prompt: routing-policy-surcharge-removal

Optimise the following Route 53 hosted zone for cost. Walk the routing
policy and query volume decision framework and emit the standard
optimization block (TARGET, VERDICT, REASON, RECOMMENDATION,
ESTIMATED_SAVINGS, REMEDIATION_STEPS).

HostedZoneId: Z-routing-policy-surcharge-removal
DomainName: single-region-app.example.com
ZoneType: Public
RecordCount: 8 (SOA, NS, 2 A records with latency-based routing, 4 supporting records)
HealthChecks: 2 (endpoint-based, justified for failover)
QueryVolume: 200M queries/month (last 30 days)
  - All queries from us-east-1 (single region traffic)
DNSSEC: Disabled
QueryLogging: Disabled
RoutingPolicy: Latency-based (2 records)
TrafficPolicies: None
Region: us-east-1

Workload context: single-region application. All users are in
us-east-1. Latency-based routing was enabled during a multi-region
migration that was later cancelled. No multi-region SLO.
