# NAT Gateway Traffic Optimizer — Advanced Patterns and Recent Features

Mindset rationale, Step-0 non-obvious behaviours, double-NAT scenarios, and
recent AWS features moved verbatim from SKILL.md. Load on demand.

## Mindset — rationale and the four guiding principles

NAT Gateway optimization is a traffic-routing decision, not an
infrastructure provisioning exercise. The goal is to route traffic to
AWS services via VPC endpoints (free or break-even-positive) rather
than through NAT Gateway (always metered at $0.045/GB).

Four principles guide every recommendation:

- **Gateway Endpoints are free and should always be created if traffic
  exists.** S3 and DynamoDB Gateway Endpoints have NO hourly charge and
  NO per-GB charge. They add a persistent route in the subnet route
  table. If any S3 or DynamoDB traffic flows through NAT, the Gateway
  Endpoint is a pure saving with zero downside.
- **Interface Endpoints have a break-even threshold.** Each Interface
  Endpoint costs $0.010/hour per AZ (~$7.30/month per AZ). The break-
  even is ~160 GB/month per AZ at $0.045/GB NAT data processing. Above
  the threshold, the Interface Endpoint saves money. Below it, NAT is
  cheaper.
- **Cross-AZ data transfer compounds NAT cost.** Traffic from a
  private subnet in AZ-1 to a NAT Gateway in AZ-2 incurs a cross-AZ
  charge ($0.01/GB each direction). This means a single NAT Gateway
  in one AZ can cost MORE than the per-GB NAT savings due to cross-AZ
  transfer charges from other AZs.
- **NAT Instance is a fixed-cost alternative for dev/test only.** A
  t3.micro NAT Instance costs ~$7.60/month (vs $32.85/month for a NAT
  Gateway). But it has no SLA, limited throughput (~5 Gbps), and is a
  single point of failure. Reserve for non-production.

## Step 0: Non-obvious behaviours that change the recommendation

These operational gotchas route a recommendation away from the obvious
choice:

- **Gateway Endpoints are FREE and persistent.** Unlike Interface
  Endpoints, S3 and DynamoDB Gateway Endpoints have no hourly charge and
  no per-GB charge. They add a route in the subnet's route table that
  persists. Always create them if any S3 or DynamoDB traffic exists.

- **Interface Endpoints are per-AZ.** An Interface Endpoint in a 3-AZ
  VPC costs $0.010/h × 3 AZs × 730h = $21.90/month. The break-even is
  ~160 GB/month per AZ. If one AZ has high traffic and others don't,
  create the Interface Endpoint in select AZs only.

- **Cross-AZ transfer ($0.01/GB each direction) compounds NAT cost.**
  When a private subnet in AZ-1 routes to a NAT Gateway in AZ-2, the
  cross-AZ hop costs $0.01/GB each way ($0.02/GB round-trip). At 500
  GB/month cross-AZ, that's $10/month on top of the NAT per-GB charge.
  This is the hidden cost of single-NAT-Gateway topologies.

- **NAT Gateway delete takes minutes but EIP release is immediate.**
  After `delete-nat-gateway`, the gateway enters `deleting` state, then
  `deleted`. The Elastic IP is disassociated but NOT released. Use
  `release-address` to stop the EIP charge ($0.005/hour if unattached).

- **Gateway Endpoint route is in the main route table.** When you
  create a Gateway Endpoint, AWS adds a `pl-xxxxxxxx` prefix list route
  to the specified route tables. If you use a main route table with
  subnet-specific overrides, the endpoint route must be in EACH subnet's
  route table, not just the main one.

- **ECR traffic is often the #2 NAT cost after S3.** Docker image
  pulls from ECR go through NAT by default. An ECR Interface Endpoint
  eliminates this. At 100+ GB/month of ECR traffic, the Interface
  Endpoint is break-even positive.

- **CloudFront can front origin via VPC endpoint.** If your origin is
  in a private subnet (ALB or EC2), CloudFront routes to the origin via
  the public internet. If the origin is an S3 bucket, use a CloudFront
  Origin Access Identity (OAI) or Origin Access Control (OAC) to keep
  traffic within AWS — no NAT needed.

- **PrivateLink (Interface Endpoint) works for SaaS APIs.** If your
  workload calls a third-party SaaS API (e.g., Datadog, Splunk, GitHub)
  through NAT, check if the SaaS offers a PrivateLink endpoint. The
  Interface Endpoint cost may be less than the NAT per-GB charge for
  high-volume API calls.

- **NAT Instance throughput is limited.** A t3.micro-based NAT Instance
  maxes out at ~1 Gbps. For dev/test this is fine; for production, it
  is a bottleneck. NAT Gateway scales to 100 Gbps.

- **S3 Gateway Endpoint requires a bucket policy adjustment.** If your
  S3 bucket policy restricts access by VPC or source IP, the Gateway
  Endpoint changes the source. Update bucket policies to include the
  endpoint ID if needed.

## Common double-NAT scenarios

Double-NAT occurs when traffic traverses TWO NAT devices before
reaching the internet. This doubles the data processing charge.

**Common double-NAT scenarios:**
```
1. Transit Gateway → NAT Gateway → Internet
   (TGW routes to a VPC with NAT, but the source VPC also has NAT)

2. VPC Peering → NAT Gateway → Internet
   (Peered VPC routes internet traffic through a VPC with NAT)

3. Private subnet → NAT Gateway (AZ-1) → NAT Gateway (AZ-2)
   (Misconfigured route tables chain two NAT Gateways)
```

## Recent AWS features (2024-2026)

- **Gateway Load Balancer Endpoint (2024-2025):** For inserting security
  appliances (firewalls, IDS/IPS) into the traffic path. Relevant when
  NAT traffic must be inspected — the GWLB Endpoint routes traffic
  through a security VPC before NAT.
- **VPC Endpoint policy enhancements (2024):** Endpoint policies now
  support more granular IAM-style permissions. Use endpoint policies to
  restrict which S3 buckets or DynamoDB tables are accessible through
  the endpoint.
- **CloudWatch NAT Gateway metrics expansion (2024-2025):** Added
  `ErrorPortAllocation` and `ConnectionEstablishedCount` metrics for
  better port-exhaustion diagnosis. Port exhaustion occurs when a NAT
  Gateway runs out of ephemeral ports (55,000 per connection per
  destination).
- **PrivateLink for AWS services expansion (2024-2025):** Additional
  AWS services now support Interface Endpoints, including some
  bedrock, securityhub, and config APIs.
- **NAT Gateway bandwidth monitoring (2024):** CloudWatch now provides
  per-destination-IP flow metrics for NAT Gateways, enabling more
  granular traffic analysis without VPC Flow Logs.
- **ECR Interface Endpoint performance (2024):** Docker pull throughput
  through ECR Interface Endpoints improved with connection reuse. Break-
  even threshold effectively lower for CI/CD-heavy workloads.
