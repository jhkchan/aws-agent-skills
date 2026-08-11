# Eval prompt: unused-zone-deletion

Optimise the following Route 53 hosted zone for cost. Walk the zone
inventory and health check decision framework and emit the standard
optimization block (TARGET, VERDICT, REASON, RECOMMENDATION,
ESTIMATED_SAVINGS, REMEDIATION_STEPS).

HostedZoneId: Z-unused-zone-deletion
DomainName: legacy-staging.example.com
ZoneType: Public
RecordCount: 4 (SOA, NS, 1 A record pointing at deleted ALB, 1 TXT)
HealthChecks: 2 (endpoint-based, 30s interval, monitoring deleted ALB)
QueryVolume: 0 queries (last 30 days, CloudWatch DNSQueries Sum = 0)
DNSSEC: Enabled (1 KMS key, $1/month)
QueryLogging: Enabled (CloudWatch Logs, ~0 GB due to no queries)
RoutingPolicy: Simple
TrafficPolicies: None
Region: us-east-1

ACM certificates referencing this zone: None
SES domain verification records: None
