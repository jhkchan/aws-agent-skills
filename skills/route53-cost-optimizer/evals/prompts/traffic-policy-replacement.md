# Eval prompt: traffic-policy-replacement

Optimise the following Route 53 hosted zone for cost. Walk the traffic
policy decision framework and emit the standard optimization block
(TARGET, VERDICT, REASON, RECOMMENDATION, ESTIMATED_SAVINGS,
REMEDIATION_STEPS).

HostedZoneId: Z-traffic-policy-replacement
DomainName: marketing-site.example.com
ZoneType: Public
RecordCount: 6 (SOA, NS, 2 A records via traffic policy, 2 CNAME)
HealthChecks: 0
QueryVolume: 50K queries/month (last 30 days)
DNSSEC: Disabled
QueryLogging: Disabled
RoutingPolicy: Traffic Policy (weighted 80/20 split)
TrafficPolicies: 1 active ($50/month)
  - Rule: 80% to primary endpoint, 20% to secondary
  - This is achievable with weighted record-level routing
Region: us-east-1

Workload context: marketing landing page. 80/20 blue-green deployment
split. No complex geoproximity or multi-region logic. Weighted
record-level routing achieves the same result at $0.
