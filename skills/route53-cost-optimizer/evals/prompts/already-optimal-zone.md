# Eval prompt: already-optimal-zone

Optimise the following Route 53 hosted zone for cost. Walk the full
decision framework and emit the standard optimization block (TARGET,
VERDICT, REASON, RECOMMENDATION, ESTIMATED_SAVINGS, REMEDIATION_STEPS).

HostedZoneId: Z-already-optimal-zone
DomainName: production.example.com
ZoneType: Public
RecordCount: 15 (SOA, NS, 10 A/AAAA records, 3 MX, 1 TXT)
HealthChecks: 3 (endpoint-based, each monitoring a unique endpoint)
QueryVolume: 500M queries/month (last 30 days, healthy traffic)
DNSSEC: Enabled (compliance requirement — PCI-DSS)
QueryLogging: Disabled
RoutingPolicy: Simple + Weighted (no surcharge)
TrafficPolicies: None
Region: us-east-1

Workload context: production e-commerce domain. DNSSEC required by
PCI-DSS compliance. Health checks monitor 3 unique API endpoints for
DNS failover. Simple and weighted routing only (no latency or geo
surcharges). No query logging needed.
