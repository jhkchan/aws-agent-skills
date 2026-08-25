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

## Mindset — the four networking realities (moved from SKILL.md)

- **Gateway endpoints are free and binary.** No break-even calculation
  applies; the only reason not to have them is a route-table or endpoint-
  policy constraint. Treat absence as a misconfiguration (like an open
  security group). Recommendation is unconditional.

- **Interface endpoints require traffic evidence, not assumptions.** An
  Interface endpoint carries a fixed ~$7.30/month per AZ plus $0.01/GB. Pull
  VPC Flow Logs or Cost Explorer service-level data to quantify GB/month
  before recommending — on a low-traffic VPC, an Interface endpoint
  INCREASES cost. The break-even threshold (~160 GB/month per AZ) is the
  load-bearing gate.

- **Cross-AZ data transfer is the hidden tax on single-NAT topology.**
  Traffic from other AZs to a single NAT Gateway crosses the AZ boundary
  twice ($0.01/GB each direction). For high-throughput workloads, cross-AZ
  cost can EXCEED the base-cost saving of consolidating. Topology
  recommendations must cite environment AND cross-AZ traffic volume.

- **NAT Instance is not a drop-in replacement.** A t3.micro NAT Instance
  costs ~$8/month flat but caps at ~1 Gbps, has no HA, and requires manual
  failover. Appropriate ONLY for dev/test. Production traffic on a NAT
  Instance is a reliability incident waiting to happen — always surface the
  reliability warning (single point of failure, no SLA).

## Step 0 summary — non-obvious NAT Gateway and VPC endpoint behaviours (moved from SKILL.md)

These behaviours are easy to misjudge without operational networking
experience. Each changes a recommendation if ignored. See
`references/expert-knowledge.md` for the full treatment. Summary:

- **Gateway endpoints are free and regional** — no per-GB or per-hour
  charge; cover only same-region S3/DynamoDB; only affect VPC-to-service
  (outbound) traffic.
- **Interface endpoint break-even is per-service, not aggregate** —
  ~160 GB/month per AZ; each AZ adds $7.30/month base; specify only the
  AZs that originate traffic.
- **Cross-AZ transfer ($0.01/GB each direction) taxes single-NAT
  topology** — model both base cost and cross-AZ transfer before
  consolidating.
- **NAT Instance is fixed-cost but capped and not HA** — appropriate
  only for dev/test; requires `--no-source-dest-check`; does not support
  port forwarding.
- **Deleting a NAT Gateway does NOT release its Elastic IP** — always
  pair deletion with `aws ec2 release-address` (orphan EIP = $3.65/mo).
- **Filter VPC Flow Logs by the NAT Gateway ENI** to isolate
  processing-charge traffic; post-endpoint traffic will not appear on
  the NAT ENI, confirming the endpoint works.
- **Gateway and Interface endpoints for S3 are different constructs** —
  always prefer the free Gateway endpoint; Interface (PrivateLink) is
  only for cross-region or private-DNS requirements.
