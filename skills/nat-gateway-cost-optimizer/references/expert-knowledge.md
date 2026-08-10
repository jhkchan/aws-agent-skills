# NAT Gateway and VPC Endpoint Expert Knowledge

Load this reference for the non-obvious networking FinOps behaviours
that change a recommendation if ignored. Each item below has been
distilled from operational experience and is easy to misjudge without
that background.

## Gateway endpoint behaviours

- **A Gateway endpoint does NOT have a per-GB or per-hour charge — it
  is genuinely free.** This is the single most misunderstood VPC
  pricing fact. The S3 and DynamoDB Gateway endpoints appear in the
  route table and reroute traffic through the AWS network backbone
  instead of through the NAT Gateway. There is no ENI, no hourly
  charge, and no data-processing fee. The only "cost" is the route-
  table entry, which is free. If any S3 or DynamoDB traffic flows
  through a NAT Gateway, the absence of the Gateway endpoint is a
  guaranteed saving.

- **A Gateway endpoint only affects traffic from the VPC to the
  service — it does not affect traffic FROM S3 TO the VPC.** S3
  cannot initiate a connection to a private subnet; the Gateway
  endpoint optimises the outbound (GET, PUT) direction. For event-
  driven architectures where S3 triggers Lambda or EventBridge, the
  Gateway endpoint still applies to the Lambda-to-S3 API calls within
  the VPC configuration.

- **Gateway endpoints are regional.** A Gateway endpoint for S3 in
  us-east-1 does NOT cover S3 buckets in eu-west-1. If the workload
  accesses cross-region S3 buckets, the traffic still goes through
  NAT (or through a regional Interface endpoint + Transit Gateway).
  Surface cross-region S3 access as a finding.

- **Gateway endpoints and Interface endpoints for the same service
  are different constructs.** S3 has BOTH a Gateway endpoint (free)
  and an Interface endpoint (PrivateLink, paid). For cost
  optimisation, always prefer the Gateway endpoint for S3. The
  Interface endpoint is only needed for cross-region access or for
  workloads that require a private IP for DNS resolution (rare).

- **Endpoint policies can restrict which resources an endpoint can
  access.** A misconfigured endpoint policy on an S3 Gateway endpoint
  can silently block access to legitimate buckets. Always review the
  endpoint policy and the IAM policy together when an endpoint
  "doesn't work."

## Interface endpoint behaviours

- **Interface endpoint pricing is per-AZ-per-hour plus per-GB.** An
  Interface endpoint creates an ENI in EACH subnet (AZ) you specify.
  A 3-AZ VPC with an ECR Interface endpoint in all 3 AZs pays
  $7.30 × 3 = $21.90/month in base cost, regardless of traffic
  volume. Always specify the minimum set of AZs that covers the
  workloads generating the traffic.

- **The break-even threshold (~160 GB/month) is per-service, not
  aggregate.** You cannot aggregate S3 (100 GB) + ECR (60 GB) to hit
  a single break-even. Each Interface endpoint is a separate
  financial decision with its own break-even. Gateway endpoints (S3,
  DynamoDB) are exempt because they are free — always create them.

## Cross-AZ and topology behaviours

- **Cross-AZ data transfer ($0.01/GB each direction) applies when a
  private subnet in AZ-B sends traffic to a NAT Gateway in AZ-A.**
  The traffic crosses the AZ boundary twice (to the gateway and
  back). For a single-NAT-Gateway topology, the cross-AZ cost =
  `total_GB × $0.02` (both directions). This can exceed the base-cost
  saving of consolidating from 3 to 1 gateway.

- **A NAT Gateway in a public subnet serves private subnets in the
  SAME VPC.** Cross-VPC NAT (via Transit Gateway or VPC peering)
  routes the traffic through the peering connection first, then
  through the NAT. The data-processing charge applies to the traffic
  as it exits the NAT, regardless of the source VPC. Surface cross-
  VPC NAT topology as a finding.

## NAT Instance behaviours

- **A NAT Instance has no per-GB processing charge — it is a fixed-
  cost EC2 host.** This makes it dramatically cheaper than a NAT
  Gateway for high-bandwidth dev/test workloads (1 TB/month through a
  NAT Instance costs the same as 0 GB). BUT: the bandwidth is capped
  by the instance type (t3.micro ~1 Gbps aggregate; t3.medium ~up to
  5 Gbps with ENA), and the instance is a single point of failure.
  Source/destination checks must be disabled
  (`modify-instance-attribute --no-source-dest-check`).

- **NAT Gateway does not support port forwarding.** If the workload
  needs inbound port mapping (e.g., a legacy NAT rule), a NAT
  Instance with iptables is required. This is an architectural
  constraint, not a cost decision — surface it as a finding.

## Elastic IP and deletion behaviours

- **Deleting a NAT Gateway does not delete its Elastic IP.** The EIP
  remains allocated and incurs $0.005/hour ($3.65/month) until
  released. Always pair a NAT Gateway deletion with
  `aws ec2 release-address` for the associated EIP.

- **VPC Flow Logs capture the interface ID of the NAT Gateway ENI.**
  Filter Flow Logs by the NAT Gateway's ENI to isolate the traffic
  that incurs processing charges. Traffic to S3 (after the Gateway
  endpoint is created) will NOT appear on the NAT ENI — confirming
  the endpoint is working.
