# Eval prompt: health-check-calculated-conversion

Optimise the following Route 53 hosted zone for cost. Walk the health
check decision framework and emit the standard optimization block
(TARGET, VERDICT, REASON, RECOMMENDATION, ESTIMATED_SAVINGS,
REMEDIATION_STEPS).

HostedZoneId: Z-health-check-calculated-conversion
DomainName: api.example.com
ZoneType: Public
RecordCount: 20 (SOA, NS, 8 A records with failover, 10 health check references)
HealthChecks: 12 endpoint-based ($0.50/month each = $6.00/month)
  - 3 checks monitor the same ALB that has target group health checks (redundant)
  - 9 checks monitor unique endpoints (justified)
QueryVolume: 450M queries/month (last 30 days)
DNSSEC: Disabled
QueryLogging: Disabled
RoutingPolicy: Failover (no surcharge)
TrafficPolicies: None
Region: us-east-1

Workload context: multi-region API with DNS failover. 3 health checks
duplicate ALB target group health monitoring.
