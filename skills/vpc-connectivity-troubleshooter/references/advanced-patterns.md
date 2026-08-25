# Advanced Patterns — VPC Connectivity Troubleshooter

Mindset, philosophy, Step-0 expert-knowledge deep dives, and recent-feature notes moved out of the SKILL.md body. Loaded on demand.

## Mindset

A "the network is broken" page is usually a routing or security-group
incident wearing a service-down costume. The destination service is
often healthy; the broken thing is the packet path between source and
destination. Treat the destination service as innocent until every OSI
layer between source and destination is proven clean. Senior network
engineers do not start with the destination's application logs; they
start with the route table and the security group, and only open the
application once L3-L4 reachability is confirmed.

## Philosophy

Four behaviours separate a senior VPC network engineer from a generalist:

- **OSI ordering is non-negotiable.** A "connection timed out" tells
  you the SYN packet did not round-trip; that constrains the cause to
  L3-L4 (routing, SG, NACL, cross-VPC plumbing). A "connection refused"
  tells you the SYN reached a port with no listener — that is a
  destination-side issue (instance down, app not running, wrong port),
  not a VPC issue. A "DNS resolution failed" tells you L7 DNS is broken
  before any packet leaves the host. Routing the symptom to the wrong
  layer is the #1 source of wasted cycles in connectivity incidents.

- **Security groups are stateful; NACLs are stateless.** A SG inbound
  allow on 443 implicitly allows the return SYN-ACK. A NACL inbound
  allow on 443 ALSO requires an outbound allow on the ephemeral range
  (1024-65535) because the return SYN-ACK is a separate NACL
  evaluation. The default NACL allows all traffic both ways; a custom
  NACL with a restrictive inbound list and a default outbound deny
  silently breaks the return path. Always evaluate the NACL in both
  directions for the connection's source port (ephemeral) and
  destination port.

- **Overlapping CIDRs between peered VPCs are a silent failure.** AWS
  refuses to route traffic for a CIDR that exists on both sides of a
  peering connection — the route appears in the table but packets do
  not deliver. There is no error event; the symptom is "the peering is
  Active but the destination is unreachable." The diagnostic is to
  compare the VPC CIDRs of both sides; overlapping CIDRs require a
  renumbering or a Transit Gateway with a translation / overlay
  (Privatelink).

- **SG references (`sg-xxx`) only resolve within the same VPC or a
  peered VPC.** A SG rule that references `sg-xxx` from an unrelated
  VPC (no peering in the route table) is silently ignored — the rule
  appears valid in the console but never matches traffic. Cross-VPC
  callers (TGW-attached VPC, unrelated peered VPC) referenced by SG-id
  silently fail; they must be expressed as CIDR blocks or as a
  referenced SG in a peered VPC with peering in the route table.

## Step 0: Non-obvious behaviours that change diagnosis

These are the operational gotchas a senior VPC engineer knows from
incident experience. Each one routes a diagnosis away from the obvious
layer to a less obvious one:

- **Security group references across VPCs do not resolve.** A SG rule
  referencing `sg-xxx` works only when the source SG is in the SAME VPC
  OR in a peered VPC with peering in the route table. A cross-VPC caller
  (TGW-attached VPC, unrelated peered VPC) referenced by SG-id silently
  fails — the rule appears correct in the console but never matches
  inbound traffic. Cross-VPC callers must use CIDR blocks or a referenced
  SG in the peered VPC (with peering enabled for the route). Operators
  who "see the SG allows sg-app" miss that sg-app is in a different VPC
  and the rule is dead.

- **NACLs are stateless; SGs are stateful.** A SG inbound allow on 443
  implicitly allows the SYN-ACK back. A NACL inbound allow on 443 also
  requires an outbound allow on the ephemeral range (1024-65535) because
  the return SYN-ACK is a separate NACL evaluation. The default NACL
  allows all traffic both ways; a custom NACL with a restrictive inbound
  list and a default outbound deny silently breaks the return path.
  Always evaluate the NACL in both directions for the connection's
  source port (ephemeral) and destination port.

- **Overlapping CIDRs between peered VPCs are a silent failure.** AWS
  refuses to route traffic for a CIDR that exists on both sides of a
  peering connection — the route appears in the table but packets do
  not deliver. There is no error event; the symptom is "the peering is
  Active but the destination is unreachable." Overlapping CIDRs cannot
  be fixed by a route table change; they require VPC renumbering or a
  Transit Gateway with PrivateLink overlay.

- **VPC peering is NOT transitive.** A peering connection between VPC-A
  and VPC-B, and another between VPC-B and VPC-C, does NOT allow VPC-A
  to reach VPC-C via VPC-B. The transit pattern requires Transit
  Gateway. Operators who "set up peering on both legs" expect transitivity
  and are surprised.

- **VPC DNS resolution and support are independent flags.** A VPC has
  two DNS settings: `enableDnsResolution` (use the VPC's .2 address as
  a resolver) and `enableDnsHostnames` (the VPC can have private
  hostnames). Both must be true for Route 53 private hosted zones to
  resolve. Operators who set only one see intermittent DNS failures.

- **Route 53 private hosted zones must be explicitly associated with
  the VPC.** A PHZ created in account A is NOT automatically visible
  to a VPC in account B, even if the VPCs are peered. The PHZ must be
  associated with the consumer VPC (cross-account, via Shared VPC or
  Resolver Rules). Operators who "created the PHZ and it works in the
  source VPC but not the peered VPC" miss the association step.

- **VPC endpoint policies are independent of IAM.** A VPC endpoint
  policy can deny an action even when IAM allows it. The CloudTrail
  event will show AccessDenied with no hint that the VPC endpoint
  policy is the cause. The diagnostic is to bypass the endpoint (route
  over the internet or a different endpoint) and see if the call
  succeeds. VPC endpoint policies are the most overlooked layer because
  they live in the VPC console, not IAM.

- **Transit Gateway route propagation is per-attachment.** A TGW has
  its own route table; attachments must propagate their routes into
  the TGW route table. An attachment that is associated with the TGW
  route table but does not propagate its VPC CIDR is invisible to other
  attachments. Operators who "added both VPCs to the TGW" miss that
  propagation is a separate flag.

- **PrivateLink endpoint services require an NLB and an accepting
  hand-shake.** The service provider creates an endpoint service backed
  by an NLB; the consumer creates an interface endpoint and the
  provider accepts (if manual acceptance is enabled). The endpoint's
  SG must allow the consumer's source. The NLB's listener must be
  configured for the right port and protocol. Operators who "created
  the endpoint but traffic times out" often miss the SG on either
  side.

- **`telnet` / `nc -vz` from the source host is the ground truth.**
  Every other probe (route table reading, SG rule enumeration, NACL
  evaluation) is a model of the network. The actual packet round-trip
  is the only definitive test. Always run `nc -vz <dest> <port>` from
  the source host before declaring a verdict.

- **Reachability Analyzer is the next best thing to packet
  round-trip.** It builds a model of the path and reports the
  blocking layer (SG, NACL, route table, peering, TGW). It does NOT
  test the live packet; it tests the configured state. For
  intermittent issues, pair Reachability Analyzer with VPC Flow Logs.

- **VPC Flow Logs tell you whether the packet reached the destination
  ENI.** Flow Logs with `reject` action confirm the packet was dropped
  by a SG or NACL. Flow Logs with `accept` action confirm the packet
  reached the ENI but do NOT confirm the application received it (the
  app could still be down). Pair Flow Logs with the application logs
  to localise the issue.

- **Internet Gateway (IGW) is one-way for Lambda.** A Lambda function
  in a public subnet has NO internet access — the function gets no
  public IP, so traffic to the IGW has no return path. EC2 instances
  with public IPs do get a return path via the IGW. Operators who
  "placed the Lambda in the default VPC" (which is public) and cannot
  reach the internet miss this asymmetry.

- **Cross-AZ traffic in the same VPC incurs cost.** Cross-AZ data
  transfer is billable in both directions. This is not a connectivity
  issue but is worth surfacing when diagnosing why a workload is in
  a different AZ than its dependency.

## Recent AWS features (2024-2026)

- **Reachability Analyzer V2 path components (2024-2025):** Richer
  path component data including SG rule references, NACL rule
  numbers, and route table entry context. Use it to localise the
  exact rule that blocks traffic.
- **Transit Gateway multicast (2024):** Multicast routing on TGW for
  broadcast-style workloads; rarely used but worth noting for
  media-streaming patterns.
- **VPC Flow Logs with `vpc-flow-log` multi-format (2024-2025):**
  Support for parquet and JSON output formats; pairs well with
  Athena for historical packet-level analysis.
- **Network Access Analyzer (2024 GA):** Declarative network
  reachability checks (e.g., "no subnet can reach 0.0.0.0/0 on
  22"). Use for posture audits; complement Flow Logs for incident
  diagnosis.
- **Route 53 Resolver DNS Firewall (2024-2025):** Domain-list-based
  DNS filtering inside the VPC. Misconfigured lists can cause
  `DNS_RESOLUTION` failures; check the Resolver firewall rule
  associations.
- **Interface VPC endpoint private DNS overrides (2024):** Custom
  private DNS names for interface endpoints beyond the service's
  default. Operators should verify PrivateDnsEnabled plus any custom
  DNS name config when diagnosing endpoint DNS issues.
- **Transit Gateway inter-region peering default quotas raised
  (2024):** Higher attachment limits per TGW. Diagnostically, attach
  exhaustion is rarer but still possible — check the
  `VerifiedAccess*` and TGW attachment quotas for very large
  topologies.
