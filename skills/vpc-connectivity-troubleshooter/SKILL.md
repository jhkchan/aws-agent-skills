---
name: vpc-connectivity-troubleshooter
description: 'Diagnoses AWS VPC network connectivity issues through a systematic OSI-layered diagnostic tree: Layer 3 routing (missing route, wrong target IGW/NAT/TGW/peering/VPN, overlapping CIDRs on peered VPCs), Layer 4 security groups (stateful inbound, outbound return path, SG references that silently fail cross-VPC), Layer 4 NACLs (stateless both directions, ephemeral range 1024-65535), Layer 7 DNS (Route 53 private hosted zones, VPC DNS resolution settings), VPC endpoint policies, and application-level auth/SSL. Cross-VPC coverage: VPC peering (DNS flag, SG references), Transit Gateway (route table associations, propagation), and PrivateLink (interface endpoint NLB). Uses Reachability Analyzer and VPC Flow Logs. Emits ROOT_CAUSE_FOUND, NEED_MORE_INFO, or ESCALATE.'
license: Apache-2.0
compatibility: Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). Offline symptom classification works from pasted error messages and topology descriptions. Live-account diagnosis uses aws ec2 describe-route-tables, aws ec2 describe-security-groups, aws ec2 describe-network-acls, aws ec2 describe-vpc-endpoints, aws ec2 describe-vpc-peering-connections, aws ec2 describe-transit- gateway-attachments, aws ec2 describe-transit-gateway-route-tables, aws ec2...
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: 'true'
  phase: '2'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: Networking
  task_type: troubleshoot
  skill_class: capability
  lifecycle_status: active
  verdict_shape: ROOT_CAUSE_FOUND | NEED_MORE_INFO | ESCALATE
  when_to_use: Diagnosing a VPC network connectivity issue (cannot reach an endpoint, intermittent connectivity, port blocked, DNS resolution failure, cross-VPC traffic failure, VPC endpoint policy block, peering asymmetry, TGW route propagation gap), walking a symptom to the failed layer with verify and fix commands, validating why an EC2 instance / Lambda / ECS task / on-prem host cannot reach a destination, or triaging a "the network is down" page where the root cause may be routing, security groups, NACLs, DNS, endpoint policy, or cross-VPC plumbing — not necessarily the destination service itself.
  when_not_to_use: Internet egress cost audits (use vpc-flow-logs-auditor or cost- anomaly detectors), RDS-specific auth and TLS issues (use rds- connectivity-troubleshooter which specialises the L7 layer for database engines), IAM execution-role diagnostics (use iam- permission-troubleshooter), or Direct Connect / Site-to-Site VPN hardware configuration (use the carrier / device-side tooling). This skill diagnoses packet-path connectivity; it does not audit configuration posture or replace dedicated per-service troubleshooters.
  activation_triggers: VPC connection timeout, cannot reach EC2 instance, EC2 port unreachable, Lambda VPC timeout, ECS task cannot reach, security group blocking traffic, NACL dropping packets, route table missing, VPC peering not working, Transit Gateway routing, TGW routes not propagating, VPC endpoint policy blocked, DNS not resolving in VPC, Route 53 private hosted zone, cross-VPC connectivity, PrivateLink endpoint service, Reachability Analyzer, VPC Flow Logs analysis, overlapping CIDR peering, troubleshoot VPC connectivity
  invocation_schema: 'Input: either (a) a symptom description (error message, observed behaviour, "host cannot reach destination on port X", intermittent vs persistent pattern), optionally paired with the source and destination context (instance/subnet/VPC IDs, ports, protocol), OR (b) a source-destination pair plus caller context (region, AZ, observed error) for live-account diagnosis. Output: a deterministic TARGET/VERDICT/REASON/LAYER/EVIDENCE/REMEDIATION block where VERDICT ∈ {ROOT_CAUSE_FOUND, NEED_MORE_INFO, ESCALATE} and LAYER ∈ {ROUTE_TABLE_MISSING, ROUTE_TABLE_WRONG_TARGET, ROUTE_OVERLAPPING_CIDR, SG_INBOUND, SG_OUTBOUND, SG_REFERENCE_CROSS_VPC, NACL_STATELESS, DNS_RESOLUTION, DNS_PHZ_ASSOCIATION, ENDPOINT_POLICY, PEERING_INACTIVE, PEERING_DNS_RESOLUTION, PEERING_SG_REFERENCE, TGW_ROUTE_PROPAGATION, TGW_ASSOCIATION_MISSING, PRIVATELINK_ENDPOINT_SERVICE, PRIVATELINK_SG, APP_AUTH, UNKNOWN}.'
  invocation_example: "# Minimal valid input (offline symptom classification):\nSymptom: \"application on EC2 instance i-app (subnet subnet-aaa,\nSG sg-app, AZ us-east-1a, VPC vpc-source) cannot reach EC2\ninstance i-db (subnet subnet-bbb, SG sg-db, AZ us-east-1b, VPC\nvpc-target) on tcp/5432. nc -vz returns 'Connection timed out'.\nThe two VPCs are peered (pcx-aaa) and the peering status is\nActive.\"\nSource: i-app, subnet-aaa (CIDR 10.0.1.0/24 in vpc-source\n  10.0.0.0/16), SG sg-app\nDestination: i-db, subnet-bbb (CIDR 172.16.1.0/24 in vpc-target\n  172.16.0.0/16), SG sg-db\nPath: same region (us-east-1), VPC peering pcx-aaa (Active)\nObserved error: nc -vz 172.16.1.10 5432 → \"Connection timed out\""
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  keywords: VPC, connectivity, routing, route table, security group, NACL, network ACL, ephemeral port, DNS, Route 53, private hosted zone, resolver, VPC endpoint, endpoint policy, VPC peering, Transit Gateway, TGW, PrivateLink, Reachability Analyzer, VPC Flow Logs, overlapping CIDR, troubleshooting
  tags: vpc, networking, troubleshooting, routing, security-groups, nacl, dns, vpc-peering, transit-gateway, privatelink
---

# VPC Connectivity Troubleshooter

## Quick start

- **Symptom → layer map (first plausible match drives the first probe):**
  timeout / SYN no SYN-ACK → ROUTE_TABLE_MISSING /
  ROUTE_TABLE_WRONG_TARGET / ROUTE_OVERLAPPING_CIDR / SG_INBOUND /
  SG_OUTBOUND / NACL_STATELESS / PEERING_INACTIVE / TGW_ROUTE_PROPAGATION
  / PRIVATELINK_ENDPOINT_SERVICE; connection refused / TCP RST →
  destination port closed (instance-level, outside this skill's VPC
  scope — surface it); DNS NXDOMAIN / "server can't find" →
  DNS_RESOLUTION / DNS_PHZ_ASSOCIATION; HTTP 403 from AWS service →
  ENDPOINT_POLICY; cross-VPC success on IP but failure on hostname →
  PEERING_DNS_RESOLUTION.
- **Always verify with a probe, never guess.** Each layer has a single
  command that proves or disproves it. A ROOT_CAUSE_FOUND verdict
  requires positive evidence — a failing probe that matches the
  symptom — not a process of elimination that "must be the SG."
- **OSI ordering is non-negotiable.** DNS (L7) → routing (L3) → SG
  (stateful L3-L4) → NACL (stateless L4) → cross-VPC plumbing → port
  reachability (L4) → application (L7). Skipping layers produces false
  root causes.
- **Security groups are stateful; NACLs are stateless.** A SG inbound
  allow on 443 implicitly allows the return SYN-ACK. A NACL inbound
  allow on 443 ALSO requires an outbound allow on the ephemeral range
  (1024-65535) for the return packet, because NACLs evaluate each
  direction independently. Operators who "fixed the SG and still
  cannot connect" usually have a NACL denying the return path.
- **SG references (`sg-xxx`) only work within the same VPC or a peered
  VPC.** A SG rule referencing `sg-xxx` from an unrelated VPC is
  silently ignored — the rule appears valid in the console but never
  matches traffic. Use CIDR blocks or a referenced SG in the peered
  VPC (with peering in the route table).
- **ESCALATE for AWS-side incidents.** AZ-wide degradation, region-
  wide service events, and underlying host failures are not customer-
  fixable — escalate to AWS Support and surface the event ARN.

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

## Quick reference — symptom triage table

| Symptom phrase / error | Most likely layer | First probe |
|---|---|---|
| `Connection timed out`, `Operation timed out`, SYN no SYN-ACK | ROUTE_TABLE_MISSING / ROUTE_TABLE_WRONG_TARGET / ROUTE_OVERLAPPING_CIDR / SG_INBOUND / NACL_STATELESS / PEERING_INACTIVE / TGW_ROUTE_PROPAGATION | `describe-route-tables` + `describe-security-groups` + `describe-network-acls` for the source subnet |
| `Connection refused`, `ECONNREFUSED`, TCP RST after SYN | Destination port closed (instance-level — outside this skill's VPC scope) | Confirm destination instance is running and listener is bound |
| `Name or service not known`, `NXDOMAIN`, `server can't find` | DNS_RESOLUTION / DNS_PHZ_ASSOCIATION | `dig`/`nslookup` from source; `list-hosted-zones-by-vpc`; VPC DNS resolution/support settings |
| HTTP 403 / AccessDenied from an AWS service via VPC endpoint | ENDPOINT_POLICY | `describe-vpc-endpoints` (Policy, State) |
| Cross-VPC success on IP but failure on hostname | PEERING_DNS_RESOLUTION | VPC peering `AllowDnsResolutionFromRemoteVpcDomainName` flag |
| VPC peering Active but traffic times out | ROUTE_OVERLAPPING_CIDR / PEERING_SG_REFERENCE / route table missing pcx route | Compare VPC CIDRs; `describe-route-tables` for pcx route; `describe-security-groups` for SG reference scope |
| TGW attachment Active but traffic times out | TGW_ROUTE_PROPAGATION / TGW_ASSOCIATION_MISSING | `describe-transit-gateway-route-tables` for propagation; `describe-transit-gateway-attachments` for association |
| PrivateLink endpoint accepted but service unreachable | PRIVATELINK_ENDPOINT_SERVICE / PRIVATELINK_SG | `describe-vpc-endpoints` (ServiceName, State); NLB and endpoint SG allow |
| Application reaches TCP layer but auth/SSL fails | APP_AUTH | Application logs; SSL/TLS handshake details |
| None of the above, region-wide event | ESCALATE | `aws health describe-events` + AWS Service Health Dashboard |

## Pre-flight: source / destination context and AWS Health gate

Before running symptom-specific probes, gather the canonical source and
destination context and short-circuit on AWS-side events that mimic
connectivity failures. Misclassifying these produces hours of network
debugging for a problem that is not a network problem.

### Pre-flight commands

```bash
# 1. Source context — instance, subnet, VPC, SG, AZ
aws ec2 describe-instances --instance-ids <source-instance-id> --output json | \
  jq '.Reservations[].Instances[] | {VpcId, SubnetId, SecurityGroups, PrivateIpAddress, PublicIpAddress}'

aws ec2 describe-subnets --subnet-ids <source-subnet-id> --output json | \
  jq '.Subnets[] | {VpcId, CidrBlock, AvailabilityZone, AvailableIpAddressCount}'

# 2. Destination context
aws ec2 describe-instances --instance-ids <dest-instance-id> --output json 2>/dev/null || \
  aws ec2 describe-network-interfaces \
    --filters Name=private-ip-address,Values=<dest-ip> --output json

# 3. AWS Health (regional events, AZ-wide degradation)
aws health describe-events --filter eventStatusCodes=OPEN,UPCOMING \
  --region us-east-1 --output json
```

### Pre-flight short-circuits

| Signal | Effect |
|---|---|
| AWS Health open event for `AWS_EC2`, `AWS_VPC`, `AWS_DIRECTCONNECT` in the region | Likely AWS-side degradation. Surface in REMEDIATION; consider ESCALATE. |
| Source instance `State: stopped` or `terminated` | Not a connectivity issue; the source is gone. |
| Destination instance `State: stopped` or `terminated` | Not a connectivity issue; the destination is gone. Surface as ROOT_CAUSE_FOUND with `LAYER: APP_AUTH` (no listener) or `UNKNOWN`. |
| Destination AZ has a known AWS Health event | Traffic to that AZ may fail while cross-AZ paths succeed. Note the AZ-specific signal. |
| Source subnet `AvailableIpAddressCount: 0` | Subnet is exhausted; new ENIs cannot be created. Symptom is on ENI-creating workloads (Lambda VPC attach, ECS tasks). |

If the input is malformed (missing source or destination identifier,
absent symptom, no port/protocol for reachability diagnosis), emit:

```text
TARGET: <source → destination pair, or unknown>
VERDICT: NEED_MORE_INFO
REASON: Input is missing required context — at minimum a symptom
  description (timeout, refused, DNS failure), a source identifier
  (instance / subnet / IP), a destination identifier (instance / IP /
  hostname), and the port and protocol under test.
LAYER: UNKNOWN
EVIDENCE:
  - Missing: <list specific missing fields>
REMEDIATION: Re-prompt the operator for: (1) the exact error string or
  observed symptom, (2) the source identifier (EC2 instance / Lambda
  function name / ECS task / on-prem CIDR), (3) the destination
  identifier, and (4) the port/protocol under test.
```

## Process — Diagnostic decision tree (apply in symptom order)

The diagnostic tree is symptom-driven. Pick the entry point based on the
observed symptom, then walk the layer-specific probes in OSI order. Each
layer ends with either a positive root-cause confirmation (failing probe
that matches the symptom) or a pass that moves to the next layer. **Never
emit ROOT_CAUSE_FOUND without a failing probe that matches the symptom.**

### Step 0: Non-obvious behaviours that change diagnosis

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

### Step 1: Symptom entry — pick the diagnostic branch

Map the symptom to a branch and jump to that branch's section. If the
symptom matches none of the categories, route to Step 9 (ESCALATE or
NEED_MORE_INFO).

| Symptom | Branch |
|---|---|
| `Connection timed out`, SYN no SYN-ACK, `nc -vz` hangs | Step 2 — Timeout (OSI walk) |
| `Name or service not known`, `NXDOMAIN`, hostname does not resolve | Step 3 — DNS |
| HTTP 403 from AWS service via VPC endpoint | Step 4 — VPC endpoint policy |
| Cross-VPC via peering: peering Active but traffic times out | Step 5 — VPC peering |
| Cross-VPC via TGW: attachments Active but traffic times out | Step 6 — Transit Gateway |
| Cross-VPC via PrivateLink: endpoint accepted but service unreachable | Step 7 — PrivateLink |
| TCP reaches but TLS / auth fails | Step 8 — Application |
| None of the above | Step 9 — Escalate / NEED_MORE_INFO |

### Step 2: Connection timeout — OSI-aligned diagnostic tree

Symptom: SYN never receives a SYN-ACK. Tools report `Connection timed
out` or `Operation timed out`. `nc -vz <dest> <port>` or `telnet` hangs
and eventually times out. No application error (the app never saw the
connection).

Probe order (OSI-aligned; each layer must pass before the next):

#### 2a: Source reachability — confirm source IP and subnet

```bash
aws ec2 describe-instances --instance-ids <source-instance-id> --output json | \
  jq '.Reservations[].Instances[] | {VpcId, SubnetId, PrivateIpAddress, PublicIpAddress}'

aws ec2 describe-subnets --subnet-ids <source-subnet-id> --output json | \
  jq '.Subnets[] | {VpcId, CidrBlock, AvailabilityZone}'
```

Capture the source VPC, subnet CIDR, AZ, and source IP. Every
subsequent probe references these.

#### 2b: Route table — source subnet

```bash
aws ec2 describe-route-tables \
  --filters Name=association.subnet-id,Values=<source-subnet-id> --output json | \
  jq '.RouteTables[].Routes'
```

If the subnet has no explicit route table, it uses the VPC's main route
table:

```bash
aws ec2 describe-route-tables \
  --filters Name=vpc-id,Values=<source-vpc-id> Name=association.main,Values=true \
  --output json | jq '.RouteTables[].Routes'
```

- For same-VPC destination: confirm a local route to the destination
  CIDR exists.
- For cross-VPC via peering: confirm a `pcx-xxx` peering route to the
  destination VPC CIDR.
- For cross-VPC via Transit Gateway: confirm a `tgw-xxx` route.
- For internet destination: confirm route to IGW (`igw-xxx`) for
  instances with public IP, OR route to NAT (`nat-xxx`) for private
  instances / Lambda.

If no route exists for the destination CIDR, **ROOT_CAUSE_FOUND** with
`LAYER: ROUTE_TABLE_MISSING`.

If a route exists but the target is wrong (e.g., IGW for a Lambda
function that needs NAT, or NAT for an internal destination that
needs a peering route), **ROOT_CAUSE_FOUND** with
`LAYER: ROUTE_TABLE_WRONG_TARGET`.

#### 2c: Route table — destination subnet (return path)

Mirror of 2b for the destination subnet. The SYN-ACK must route back.
For cross-VPC, the destination subnet's route table must have the
peering/TGW route back to the source VPC CIDR.

#### 2d: Overlapping CIDRs — silent peering failure

```bash
aws ec2 describe-vpcs --vpc-ids <source-vpc-id> <dest-vpc-id> --output json | \
  jq '.Vpcs[] | {VpcId, CidrBlock, CidrBlockAssociationSet}'
```

If the source VPC CIDR and destination VPC CIDR overlap (e.g., both
`10.0.0.0/16`), AWS silently refuses to route traffic between them via
peering. The route table may show the `pcx-xxx` route but packets do
not deliver. **ROOT_CAUSE_FOUND** with
`LAYER: ROUTE_OVERLAPPING_CIDR`. The fix is VPC renumbering or a TGW
with PrivateLink overlay (translation).

#### 2e: Security group — destination inbound

```bash
aws ec2 describe-security-groups --group-ids <dest-sg-1> <dest-sg-2> --output json | \
  jq '.SecurityGroups[].IpPermissions'
```

**Match the source against the inbound rules:**
- If the rule allows `0.0.0.0/0` on the destination port → SG allows.
- If the rule allows a CIDR — does the source IP fall within it?
  - Source in same VPC: use the source's private IP.
  - Source in peered VPC: use the source's private IP in the peer
    VPC's CIDR.
  - Source on-prem/over internet: use the source's public IP or NAT
    EIP.
- If the rule references `sg-xxx` — is the source SG in the SAME VPC
  as the destination SG? Cross-VPC SG references are silently ignored.
- If the rule references a prefix list — does the prefix list contain
  the source CIDR?

If no inbound rule matches the source on the destination port,
**ROOT_CAUSE_FOUND** with `LAYER: SG_INBOUND`.

If a rule references `sg-xxx` from a different VPC (and the VPCs are
not peered with peering in the route table), **ROOT_CAUSE_FOUND** with
`LAYER: SG_REFERENCE_CROSS_VPC`. Use a CIDR block or a referenced SG
in the peered VPC instead.

#### 2f: Security group — source outbound

SGs are stateful, but the source still needs an outbound allow. The
default outbound (allow all) usually covers this, but a locked-down
source SG can block the SYN.

```bash
aws ec2 describe-security-groups --group-ids <source-sg> --output json | \
  jq '.SecurityGroups[].IpPermissionsEgress'
```

If the source's egress does not allow traffic to the destination
private IP (or the destination SG, if egress is SG-referenced),
**ROOT_CAUSE_FOUND** with `LAYER: SG_OUTBOUND` (source-side).

#### 2g: NACL — source subnet (stateless — both directions)

```bash
aws ec2 describe-network-acls \
  --filters Name=association.subnet-id,Values=<source-subnet-id> --output json | \
  jq '.NetworkAcls[].Entries'
```

**Inbound** (return SYN-ACK from destination to source's ephemeral
port):
- Rule allow on the destination port from the destination CIDR to the
  source's ephemeral port range (1024-65535).
- Default NACL allows all; custom NACLs often miss this.

**Outbound** (initial SYN from source to destination port):
- Rule allow on the destination port to the destination CIDR.

If either direction denies, **ROOT_CAUSE_FOUND** with
`LAYER: NACL_STATELESS` (source-side).

#### 2h: NACL — destination subnet (mirror of 2g)

Same logic, mirrored. Fetch the NACL for the destination subnet and
verify inbound on destination port + outbound on ephemeral range. A
common pattern is a custom NACL on the destination subnet that allows
inbound on the listener port but has no explicit outbound allow on
the ephemeral range, silently dropping the SYN-ACK.

#### 2i: After all SG/NACL/route layers pass — final reachability probe

From the source host:

```bash
# TCP reachability (should succeed if all above passed)
nc -vz <dest-ip-or-hostname> <port>

# Or:
telnet <dest-ip-or-hostname> <port>
```

If `nc -vz` succeeds but the application still times out, the issue is
likely client-side (connection pool, driver config, JVM DNS cache) —
emit ROOT_CAUSE_FOUND with `LAYER: UNKNOWN` and a client-side note, or
NEED_MORE_INFO if the caller context is incomplete.

If `nc -vz` fails intermittently, use VPC Flow Logs to localise:

```bash
aws ec2 describe-flow-logs \
  --filter Name=resource-id,Values=<source-eni> --output json

# Query the Flow Logs log group (e.g., via CloudWatch Logs Insights)
aws logs start-query \
  --log-group-name <flow-logs-group> \
  --start-time $(date -d '-1 hour' +%s) --end-time $(date +%s) \
  --query-string 'fields @timestamp, srcAddr, dstAddr, srcPort, dstPort,
    action | filter (srcAddr = "<source-ip>" and dstAddr = "<dest-ip>")
    or (srcAddr = "<dest-ip>" and dstAddr = "<source-ip>") | limit 50'
```

`action: REJECT` confirms the packet was dropped by a SG or NACL.
`action: ACCEPT` confirms the packet reached the ENI but does not
confirm the application received it.

#### 2j: Reachability Analyzer (cross-layer automated path analysis)

```bash
# Create a path between source and destination
PATH_ID=$(aws ec2 create-network-insights-path \
  --source <source-eni-id> \
  --destination <dest-eni-id> \
  --destination-port <port> \
  --protocol tcp \
  --output json | jq -r '.NetworkInsightsPath.NetworkInsightsPathId')

# Run the analysis
ANALYSIS_ID=$(aws ec2 start-network-insights-analysis \
  --network-insights-path-id $PATH_ID \
  --output json | jq -r '.NetworkInsightsAnalysis.NetworkInsightsAnalysisId')

# Wait for completion, then read the result
aws ec2 describe-network-insights-analyses \
  --network-insights-analysis-ids $ANALYSIS_ID --output json | \
  jq '.NetworkInsightsAnalyses[0] | {Status, ForwardPathComponents,
    Explanations}'
```

Reachability Analyzer returns the path component that blocks traffic
(e.g., "Outbound rule of sg-xxx denies traffic on port 443"). Use it
to confirm a SG/NACL/route diagnosis when manual probes are
inconclusive.

### Step 3: DNS resolution failure

Symptom: hostname does not resolve. Tools report `NXDOMAIN`, `server
can't find`, `Name or service not known`.

```bash
# From the source host
nslookup <hostname>
dig <hostname>

# What resolver is the source using?
aws ec2 describe-vpcs --vpc-ids <source-vpc-id> --output json | \
  jq '.Vpcs[] | {VpcId, CidrBlock,
    DhcpOptionsId: .DhcpOptionsId}'

aws ec2 describe-dhcp-options \
  --dhcp-options-ids <dhcp-options-id> --output json | \
  jq '.DhcpOptions.Configurations'
```

The DHCP options set `domain-name-servers` should be
`AmazonProvidedDNS` (169.254.169.53 / VPC `.2` address) for AWS DNS
resolution. Custom resolvers require a Route 53 Resolver inbound
endpoint in the VPC.

#### 3a: VPC DNS settings

```bash
aws ec2 describe-vpc-attribute --vpc-id <source-vpc-id> \
  --attribute enableDnsSupport --output json
aws ec2 describe-vpc-attribute --vpc-id <source-vpc-id> \
  --attribute enableDnsHostnames --output json
```

Both `enableDnsSupport` and `enableDnsHostnames` must be `true` for:
- Route 53 private hosted zones to resolve.
- VPC private hostnames (e.g., `ec2-10-0-1-10.us-east-1.compute.internal`)
  to resolve.

If either is false, **ROOT_CAUSE_FOUND** with `LAYER: DNS_RESOLUTION`.

#### 3b: Route 53 private hosted zone association

```bash
aws route53 list-hosted-zones-by-vpc \
  --vpc-id <source-vpc-id> --vpc-region us-east-1 --output json

aws route53 list-hosted-zones --output json | \
  jq '.HostedZones[] | {Id, Name, Config: .Config}'
```

For cross-account PHZs:
- The PHZ must be associated with the consumer VPC (cross-account
  association via Shared VPC, Resource Access Manager, or the
  `list-hosted-zones-by-vpc` API).
- Alternatively, a Route 53 Resolver Rule can forward queries from
  the consumer VPC to the PHZ owner's Resolver inbound endpoint.

If the PHZ is not associated with the source VPC, **ROOT_CAUSE_FOUND**
with `LAYER: DNS_PHZ_ASSOCIATION`.

#### 3c: Resolver endpoints and rules

```bash
aws route53resolver list-resolver-endpoints \
  --filters Name=VpcId,Values=<source-vpc-id> --output json

aws route53resolver list-resolver-rules --output json | \
  jq '.ResolverRules[] | {Id, Name, DomainName, RuleType}'
```

A `SYSTEM` rule for `.` (root) forwards everything to AmazonProvidedDNS.
A `FORWARD` rule forwards specific domains to a target IP (e.g., on-prem
DNS). Conflicting rules can shadow each other; the more specific domain
wins.

If a forward rule is misconfigured (target IP unreachable, port
mismatch), DNS for the rule's domain fails. **ROOT_CAUSE_FOUND** with
`LAYER: DNS_RESOLUTION`.

### Step 4: VPC endpoint policy

Symptom: an AWS service API call returns AccessDenied when made from
within a VPC, but the same call succeeds from outside the VPC (or from
a different VPC). The IAM role and identity-based policy are correct.

```bash
aws ec2 describe-vpc-endpoints \
  --filters Name=vpc-id,Values=<source-vpc-id> --output json | \
  jq '.VpcEndpoints[] | {ServiceName, State, Policy, PrivateDnsEnabled}'
```

A VPC endpoint policy is independent of IAM. It can allow or deny
specific actions, principals, and resources. Common restrictive patterns:

- Policy allows `s3:GetObject` only — `s3:PutObject` is denied even
  though IAM allows it.
- Policy restricts to a specific bucket ARN — other buckets are denied.
- Policy requires a specific VPC or VPC endpoint condition.

To verify the endpoint is the cause, bypass it:
- For an S3 Gateway endpoint: remove the endpoint temporarily, or test
  from a subnet without the prefix list in its route table.
- For an Interface endpoint: route via NAT Gateway or a different VPC.

If bypassing the endpoint makes the API call succeed,
**ROOT_CAUSE_FOUND** with `LAYER: ENDPOINT_POLICY`. Fix: scope the
endpoint policy to allow the required action, OR add the action to the
existing Allow statement.

### Step 5: VPC peering — Active but traffic times out

```bash
aws ec2 describe-vpc-peering-connections \
  --filters Name=requester-vpc-info.vpc-id,Values=<source-vpc-id> \
            Name=status-code,Values=active --output json | \
  jq '.VpcPeeringConnections[] | {Id, Status: .Status.Code,
    RequesterVpcInfo, AccepterVpcInfo}'
```

For each peering connection:

#### 5a: Status check

| Status | Effect |
|---|---|
| `active` | Peering is up; continue with route and SG checks. |
| `pending-acceptance` | Accepter has not accepted. Traffic does not flow. **ROOT_CAUSE_FOUND**, `LAYER: PEERING_INACTIVE`. Accepter accepts. |
| `rejected`, `failed`, `expired`, `deleted` | Peering is non-functional. **ROOT_CAUSE_FOUND**, `LAYER: PEERING_INACTIVE`. Recreate the peering request. |
| `provisioning` | Peering is being established; wait. |

#### 5b: Route table — both sides

Both the requester and accepter VPCs' route tables must have a route
to the other VPC's CIDR via the `pcx-xxx` peering connection. A common
failure: only the requester side has the route; the accepter side
forgets to add it.

```bash
aws ec2 describe-route-tables \
  --filters Name=vpc-id,Values=<requester-vpc-id> --output json | \
  jq '.RouteTables[].Routes[] | select(.VpcPeeringConnectionId != null)'

aws ec2 describe-route-tables \
  --filters Name=vpc-id,Values=<accepter-vpc-id> --output json | \
  jq '.RouteTables[].Routes[] | select(.VpcPeeringConnectionId != null)'
```

If either side is missing the `pcx-xxx` route, traffic fails. The fix
is `create-route --route-table-id <rtb> --destination-cidr-block
<peer-cidr> --vpc-peering-connection-id <pcx>`.

#### 5c: Overlapping CIDRs

See Step 2d. Overlapping CIDRs are a silent failure on peering.

#### 5d: Security group references

A SG rule in the requester VPC can reference a SG in the accepter VPC
BY ID, IF the peering connection is in the route table. Without the
route, the reference is silently ignored. Confirm the peering route
exists (5b) before trusting a cross-VPC SG reference.

If a cross-VPC SG reference is used and the peering route is missing,
the rule is dead. **ROOT_CAUSE_FOUND** with `LAYER: PEERING_SG_REFERENCE`.

#### 5e: DNS resolution from remote VPC

```bash
aws ec2 describe-vpc-peering-connections \
  --vpc-peering-connection-ids <pcx-id> --output json | \
  jq '.VpcPeeringConnections[] | {
    RequesterDns: .RequesterVpcInfo.AllowDnsResolutionFromRemoteVpcDomainName,
    AccepterDns: .AccepterVpcInfo.AllowDnsResolutionFromRemoteVpcDomainName}'
```

If the symptom is "IP works but hostname does not" across peered VPCs,
the `AllowDnsResolutionFromRemoteVpcDomainName` flag is false on one
side. **ROOT_CAUSE_FOUND** with `LAYER: PEERING_DNS_RESOLUTION`. Both
VPCs must have `enableDnsSupport` AND `enableDnsHostnames` true, and
the requester side must enable the remote DNS resolution flag at
peering creation time.

### Step 6: Transit Gateway — attachments Active but traffic times out

```bash
aws ec2 describe-transit-gateway-attachments \
  --filters Name=resource-id,Values=<source-vpc-id> --output json | \
  jq '.TransitGatewayAttachments[]'

aws ec2 describe-transit-gateways \
  --transit-gateway-ids <tgw-id> --output json | \
  jq '.TransitGateways[] | {TransitGatewayId,
    Options: .Options.AssociationDefaultRouteTableId,
    PropagationDefaultRouteTableId}'
```

#### 6a: Attachment state

| State | Effect |
|---|---|
| `available` | Attachment is up; continue with route checks. |
| `pending`, `modifying`, `pending-acceptance` | Attachment is being established or modified; wait or accept. |
| `rejected`, `failed`, `deleted` | Attachment is non-functional. Recreate. |

#### 6b: TGW route table — association vs propagation

Each attachment is associated with exactly one TGW route table (the
"association"). Routes from the attachment's VPC can be:
- **Statically added** to a TGW route table.
- **Dynamically propagated** to one or more TGW route tables (the
  "propagation").

```bash
aws ec2 describe-transit-gateway-route-tables \
  --transit-gateway-route-table-ids <tgw-rtb-id> --output json | \
  jq '.TransitGatewayRouteTables[]'

aws ec2 get-transit-gateway-route-table-associations \
  --transit-gateway-route-table-id <tgw-rtb-id> --output json

aws ec2 get-transit-gateway-route-table-propagations \
  --transit-gateway-route-table-id <tgw-rtb-id> --output json
```

If the source VPC's attachment is associated with TGW route table A
but the destination VPC's attachment propagates only into TGW route
table B, the source cannot reach the destination.

If either attachment is missing from the TGW route table,
**ROOT_CAUSE_FOUND** with `LAYER: TGW_ASSOCIATION_MISSING` (if not
associated) or `LAYER: TGW_ROUTE_PROPAGATION` (if associated but not
propagated).

#### 6c: VPC route tables — both sides

Both VPCs' subnet route tables must have a `tgw-xxx` route to the
other VPC's CIDR. A common failure: one side has the route, the other
does not.

### Step 7: PrivateLink — endpoint accepted but service unreachable

```bash
aws ec2 describe-vpc-endpoints \
  --filters Name=vpc-id,Values=<consumer-vpc-id> \
            Name=service.service-type,Values=Interface --output json | \
  jq '.VpcEndpoints[] | {ServiceName, State, SubnetIds, Groups,
    PrivateDnsEnabled}'
```

#### 7a: Endpoint state

| State | Effect |
|---|---|
| `available` | Endpoint is up; continue with SG and NLB checks. |
| `pending`, `pending-waiting`, `pending-acceptance` | Provider must accept (if manual acceptance). Wait. |
| `rejected`, `failed`, `deleted` | Endpoint is non-functional. Provider rejected or the NLB was deleted. |

#### 7b: Endpoint SG

The endpoint's SG (consumer side) must allow inbound from the source
on the listener port. The endpoint creates an ENI in the consumer
subnet; the ENI's SG governs inbound traffic to the endpoint.

```bash
aws ec2 describe-network-interfaces \
  --filters Name=vpc-id,Values=<consumer-vpc-id> \
            Name=description,Values="VPC Endpoint Interface" --output json | \
  jq '.NetworkInterfaces[] | {NetworkInterfaceId, Groups, PrivateIpAddress}'
```

If the endpoint's SG does not allow the source, **ROOT_CAUSE_FOUND**
with `LAYER: PRIVATELINK_SG`. Fix: add an inbound rule to the
endpoint's SG.

#### 7c: Endpoint service (provider side)

```bash
aws ec2 describe-vpc-endpoint-service-configurations \
  --service-ids <service-id> --output json | \
  jq '.ServiceConfigurations[] | {ServiceName, State,
    AcceptanceRequired, NetworkLoadBalancerArns}'
```

The provider's endpoint service must be `available`. The NLB must be
healthy in the consumer's AZs. If the NLB has no healthy targets in
the consumer's AZ, traffic fails.

If the endpoint service is misconfigured (NLB deleted, listener on
wrong port), **ROOT_CAUSE_FOUND** with
`LAYER: PRIVATELINK_ENDPOINT_SERVICE`. Fix: provider restores the NLB
and listener.

#### 7d: Private DNS

If `PrivateDnsEnabled: true`, the service's DNS name resolves to the
endpoint's private IP from within the consumer VPC. If `false`, the
consumer must use the endpoint's DNS name (or IP). Operators who "use
the public DNS name" with PrivateDnsEnabled=false see traffic route
over the internet instead of the endpoint.

### Step 8: Application layer — TLS / auth

Symptom: TCP succeeds, TLS or application-layer auth fails. Common
strings: `SSL handshake failed`, `certificate verify failed`,
`unauthorised`, `403 Forbidden` (from the application, not the AWS
service).

This layer is outside the VPC's packet path; the VPC is fine. Surface
the diagnosis and route to the application-specific troubleshooter
(e.g., `rds-connectivity-troubleshooter` for database TLS, `iam-
permission-troubleshooter` for AccessDenied from the application's
IAM calls).

If the symptom is purely application-layer, **ROOT_CAUSE_FOUND** with
`LAYER: APP_AUTH`. Note that the VPC layers all passed.

### Step 9: Escalate or NEED_MORE_INFO

If none of the above produced a positive root-cause match, OR the
symptom clearly indicates an AWS-side incident (AZ-wide degradation,
region event, Direct Connect carrier issue), emit one of:

- **ESCALATE** — AWS-side incident. Surface the AWS Health event ARN
  and recommend opening a Support case. Do NOT continue diagnosing.
- **NEED_MORE_INFO** — A specific probe requires operator input. List
  the missing pieces (source instance ID, destination identifier,
  port, protocol, region) and the next probe to run once the info is
  available.

## Output format

```text
TARGET: <source → destination pair>
VERDICT: ROOT_CAUSE_FOUND | NEED_MORE_INFO | ESCALATE
REASON: <1-2 sentences naming the failed layer and the failing probe>
LAYER: <ROUTE_TABLE_MISSING | ROUTE_TABLE_WRONG_TARGET |
        ROUTE_OVERLAPPING_CIDR | SG_INBOUND | SG_OUTBOUND |
        SG_REFERENCE_CROSS_VPC | NACL_STATELESS | DNS_RESOLUTION |
        DNS_PHZ_ASSOCIATION | ENDPOINT_POLICY | PEERING_INACTIVE |
        PEERING_DNS_RESOLUTION | PEERING_SG_REFERENCE |
        TGW_ROUTE_PROPAGATION | TGW_ASSOCIATION_MISSING |
        PRIVATELINK_ENDPOINT_SERVICE | PRIVATELINK_SG | APP_AUTH |
        UNKNOWN>
EVIDENCE:
  - <observed symptom — error string or behaviour>
  - <failing probe — command and its output that confirms the cause>
  - <passing probes — layers ruled out>
REMEDIATION:
  1. <specific action with CLI command>
  2. <verification command after the fix>
CONFIRM: Before executing any state-changing CLI, emit and await operator
  approval: "CONFIRM: About to <action> on <id> in <region>. Proceed?
  (yes/no)"
```

### Worked example — SG inbound missing rule

```text
TARGET: i-app (10.0.1.10, subnet-aaa, vpc-source) → i-db
  (172.16.1.10, subnet-bbb, vpc-target) on tcp/5432
VERDICT: ROOT_CAUSE_FOUND
REASON: The destination SG sg-db has no inbound rule matching the
  source's CIDR 10.0.1.0/24 on port 5432 — the SYN is dropped at the
  instance's security group (Step 2e).
LAYER: SG_INBOUND
EVIDENCE:
  - Symptom: application on i-app (10.0.1.10) reports "Operation
    timed out" when connecting to i-db (172.16.1.10:5432). nc -vz
    hangs.
  - Probe: aws ec2 describe-security-groups --group-ids sg-db returns
    inbound rules allowing 172.16.0.0/16 (local VPC) on 5432. No
    rule matches 10.0.1.0/24 (source VPC CIDR).
  - Passing: route table for subnet-aaa has a pcx-aaa route to
    172.16.0.0/16; route table for subnet-bbb has a pcx-aaa route
    back to 10.0.0.0/16; peering pcx-aaa is Active; VPC CIDRs do not
    overlap; NACL on both subnets is the default (allow all).
REMEDIATION:
  1. Add an inbound rule to sg-db allowing the source CIDR on tcp/5432:
     aws ec2 authorize-security-group-ingress --group-id sg-db
       --protocol tcp --port 5432 --cidr 10.0.1.0/24 --profile <p>
  2. Verify from the source: nc -vz 172.16.1.10 5432 (should succeed
     within 1s).
CONFIRM: Before authorizing the SG ingress, emit and await:
  "CONFIRM: About to authorize-security-group-ingress on sg-db in
   us-east-1 for 10.0.1.0/24 on tcp/5432. Proceed? (yes/no)"
```

### Worked example — NACL missing ephemeral outbound

```text
TARGET: i-app (10.0.1.10, subnet-aaa) → i-db (172.16.1.10,
  subnet-bbb) on tcp/5432
VERDICT: ROOT_CAUSE_FOUND
REASON: The destination subnet's custom NACL (acl-bbb) has an inbound
  allow on tcp/5432 but no outbound allow on the ephemeral range
  (1024-65535) for the return SYN-ACK — the SYN reaches the
  destination but the SYN-ACK is dropped on the outbound evaluation
  (Step 2h).
LAYER: NACL_STATELESS
EVIDENCE:
  - Symptom: nc -vz 172.16.1.10 5432 from 10.0.1.10 hangs and times
    out. nc -vz in the reverse direction also fails.
  - Probe: aws ec2 describe-network-acls for subnet-bbb returns
    acl-bbb with inbound rule 100: tcp/5432 from 10.0.0.0/8 (allow)
    and outbound rule 100: tcp/5432 to 10.0.0.0/8 (allow) — but NO
    outbound rule for the ephemeral range (1024-65535). The default
    rule * denies all other outbound.
  - Passing: SG on both sides allows the rule; route table on both
    sides has the peering route; peering is Active; CIDRs do not
    overlap.
REMEDIATION:
  1. Add an outbound rule on acl-bbb for the ephemeral range back to
     the source CIDR:
     aws ec2 create-network-acl-entry --network-acl-id acl-bbb
       --rule-number 110 --protocol tcp --port-range From=1024,To=65535
       --cidr-block 10.0.0.0/8 --rule-action allow --egress --profile <p>
  2. Verify from the source: nc -vz 172.16.1.10 5432.
CONFIRM: Before modifying the NACL, emit and await operator approval.
```

### Worked example — overlapping CIDR (silent peering failure)

```text
TARGET: i-app (10.0.1.10, vpc-source 10.0.0.0/16) → i-db
  (10.0.2.10, vpc-target 10.0.0.0/16) on tcp/5432
VERDICT: ROOT_CAUSE_FOUND
REASON: The source and destination VPCs both use 10.0.0.0/16. AWS
  silently refuses to route traffic between overlapping CIDRs via
  peering. The peering connection pcx-aaa is Active but packets do
  not deliver (Step 2d).
LAYER: ROUTE_OVERLAPPING_CIDR
EVIDENCE:
  - Symptom: nc -vz 10.0.2.10 5432 from 10.0.1.10 times out despite
    peering being Active, route tables both having the pcx route,
    SGs allowing the rule, and NACLs being default.
  - Probe: aws ec2 describe-vpcs for both VPCs returns
    CidrBlock 10.0.0.0/16 for each.
  - Passing: peering Active; route tables correct; SGs correct;
    NACLs default.
REMEDIATION:
  1. Renumber one VPC to a non-overlapping CIDR (e.g., change vpc-
     target to 10.99.0.0/16). This requires recreating subnets,
     updating route tables, and migrating workloads — plan a
     maintenance window.
  2. Or migrate the connectivity to a Transit Gateway with
     PrivateLink overlay for network translation. This avoids
     renumbering but adds complexity.
  3. Verify after renumbering: nc -vz 10.0.2.10 5432 from 10.0.1.10
     (with the new subnet's IP) succeeds.
CONFIRM: VPC renumbering is a major change. Emit and await operator
  approval before any state-changing CLI.
```

### Worked example — VPC endpoint policy blocking S3 PutObject

```text
TARGET: i-app (10.0.1.10, vpc-source) → s3:PutObject on
  arn:aws:s3:::logs-bucket-prod/*
VERDICT: ROOT_CAUSE_FOUND
REASON: The S3 VPC Gateway endpoint (vpce-aaa) policy allows only
  s3:GetObject; s3:PutObject is denied by the endpoint policy even
  though the IAM role allows it. Bypassing the endpoint (over NAT)
  succeeds — confirming the endpoint policy is the cause.
LAYER: ENDPOINT_POLICY
EVIDENCE:
  - Symptom: application on i-app fails to upload to
     s3://logs-bucket-prod/ with AccessDenied. The IAM role policy
     includes s3:PutObject on the bucket ARN (verified via
     simulate-principal-policy).
  - Probe: aws ec2 describe-vpc-endpoints for vpce-aaa returns a
     policy with a single statement: Allow s3:GetObject on
     arn:aws:s3:::logs-bucket-prod/*. No statement allows
     s3:PutObject.
  - Probe: bypass the endpoint (route via a NAT Gateway in a test
     subnet) — s3:PutObject succeeds. This confirms the endpoint
     policy is the cause.
  - Passing: IAM policy allows; bucket policy allows; network
    path is fine.
REMEDIATION:
  1. Update the endpoint policy to allow s3:PutObject:
     aws ec2 modify-vpc-endpoint --vpc-endpoint-id vpce-aaa
       --policy-document '<JSON with Allow statement for
       s3:PutObject on the bucket ARN>' --profile <p>
  2. Verify from the source: re-run the upload; it should succeed.
  3. Re-enable the endpoint for production traffic once verified.
CONFIRM: Before modifying the endpoint policy, emit and await
  operator approval.
```

## STRICT output contract

This contract is mandatory. The Output format template above is the
authoritative structure; the rules below disambiguate the failure
modes that score D8=13 on this skill. Violating any rule is a
misdiagnosis.

### Required output structure

Every diagnosis MUST emit this exact block, with all fields populated
(no empty fields, no omitted sections, no reordering):

```text
TARGET: <source → destination pair, including IPs / subnets / VPCs>
VERDICT: ROOT_CAUSE_FOUND | NEED_MORE_INFO | ESCALATE
REASON: <1-2 sentences naming the failed layer and the failing probe>
LAYER: <one of the 18 LAYER enum values — never blank, never prose>
EVIDENCE:
  - <observed symptom — error string or behaviour>
  - <failing probe — command and its output that confirms the cause>
  - <passing probes — layers ruled out, with the probe that ruled them out>
REMEDIATION:
  1. <specific action with CLI command>
  2. <verification command after the fix>
CONFIRM: Before executing any state-changing CLI, emit and await operator
  approval: "CONFIRM: About to <action> on <id> in <region>. Proceed?
  (yes/no)"
```

Verdict-specific rules:
- `ROOT_CAUSE_FOUND` → LAYER is one of the 18 enum values; EVIDENCE
  includes a failing probe whose output positively confirms the cause
  (not a process of elimination); REMEDIATION is actionable CLI.
- `NEED_MORE_INFO` → LAYER is `UNKNOWN` or the best candidate; EVIDENCE
  lists the missing input (source ID, destination ID, port, protocol,
  region) and the next probe to run once it is supplied.
- `ESCALATE` → LAYER is the suspected AWS-side category; REASON cites
  the AWS Health event ARN or the carrier/out-of-band signal.

### FORBIDDEN output patterns

1. NEVER skip the NACL check — NACLs are stateless, both inbound AND
   outbound rules needed for ephemeral ports 1024-65535. A diagnosis
   that omits `describe-network-acls` for both source and destination
   subnets is incomplete, even if a SG rule matches.
2. NEVER assume a Security Group reference works cross-VPC — SG
   references (`sg-xxx`) only resolve within the same VPC or a peered
   VPC with peering in the route table, not via Transit Gateway. A
   cross-VPC SG reference via TGW is silently ignored.
3. NEVER declare ROOT_CAUSE_FOUND without a failing probe that matches
   the symptom. "It must be the SG" by process of elimination is
   forbidden — cite the `describe-security-groups` or `nc -vz` output
   that positively confirms the drop.
4. NEVER skip the OSI order for timeout symptoms. The probe order is
   DNS (L7) → routing (L3) → SG (L4) → NACL (L4) → cross-VPC plumbing
   → port reachability → application. A diagnosis that checks the SG
   before the route table and concludes "SG is fine" missed that the
   SYN never reached the SG evaluation.
5. NEVER treat VPC peering as transitive. Peering between A-B and B-C
   does NOT allow A to reach C via B — transit requires Transit
   Gateway. A diagnosis that suggests "add a peering route through
   VPC-B" is wrong.
6. NEVER assume overlapping VPC CIDRs will route via peering. They are
   a silent failure: the `pcx-xxx` route appears in the table but
   packets do not deliver. A diagnosis that lists peering Active +
   route present as "passing" without comparing the two VPC CIDRs is
   incomplete.
7. NEVER assume the VPC endpoint policy matches the IAM policy. The
   endpoint policy is an independent layer that can deny actions IAM
   allows. A diagnosis that clears IAM without bypassing the endpoint
   to verify has not ruled out `ENDPOINT_POLICY`.

### Perfect example output

```text
TARGET: i-app (10.0.1.10, subnet-aaa, vpc-source) → i-db
  (172.16.1.10, subnet-bbb, vpc-target) on tcp/5432
VERDICT: ROOT_CAUSE_FOUND
REASON: The destination SG sg-db has no inbound rule matching the
  source CIDR 10.0.1.0/24 on port 5432 — the SYN is dropped at the
  instance's security group (Step 2e).
LAYER: SG_INBOUND
EVIDENCE:
  - Symptom: application on i-app (10.0.1.10) reports "Operation
    timed out" connecting to i-db (172.16.1.10:5432). nc -vz hangs.
  - Probe: aws ec2 describe-security-groups --group-ids sg-db returns
    inbound rules allowing 172.16.0.0/16 on 5432 only — no rule
    matches 10.0.1.0/24 (source VPC CIDR).
  - Passing: route table for subnet-aaa has pcx-aaa route to
    172.16.0.0/16; route table for subnet-bbb has pcx-aaa route back
    to 10.0.0.0/16; peering pcx-aaa is Active; VPC CIDRs do not
    overlap; NACL on both subnets allows inbound 5432 AND outbound
    ephemeral 1024-65535 (verified in both directions).
REMEDIATION:
  1. Add an inbound rule to sg-db for the source CIDR on tcp/5432:
     aws ec2 authorize-security-group-ingress --group-id sg-db \
       --protocol tcp --port 5432 --cidr 10.0.1.0/24
  2. Verify from the source: nc -vz 172.16.1.10 5432 (should succeed
     within 1s).
CONFIRM: Before authorizing the SG ingress, emit and await:
  "CONFIRM: About to authorize-security-group-ingress on sg-db in
   us-east-1 for 10.0.1.0/24 on tcp/5432. Proceed? (yes/no)"
```

## Anti-Patterns — NEVER

- NEVER declare ROOT_CAUSE_FOUND without a failing probe that matches
  the symptom. A "process of elimination" diagnosis erodes operator
  trust when the real cause is elsewhere.

- NEVER skip the OSI order for timeout symptoms. If you check the
  security group before the route table and conclude "the SG is fine,
  must be the destination," you missed that the route table has no
  route for the destination CIDR — the SYN never reached the SG
  evaluation.

- NEVER evaluate NACLs in only one direction. NACLs are stateless;
  the return SYN-ACK is a separate evaluation. The most common NACL
  mistake is an inbound rule on 443 with no outbound rule on the
  ephemeral range (1024-65535).

- NEVER assume a security-group reference (`sg-xxx`) works cross-VPC.
  Cross-VPC SG references are silently ignored unless the VPCs are
  peered AND the peering is in the route table. Use CIDR blocks or a
  referenced SG in the peered VPC.

- NEVER treat VPC peering as transitive. Peering between A-B and B-C
  does NOT allow A to reach C via B. Transit requires Transit Gateway.

- NEVER assume overlapping VPC CIDRs will route via peering. They are
  a silent failure — the route appears but packets do not deliver.

- NEVER assume the VPC DNS settings are correct because "DNS works
  for some queries." Route 53 private hosted zones require BOTH
  `enableDnsSupport` AND `enableDnsHostnames` to be true. Cross-
  account PHZs require explicit association with the consumer VPC.

- NEVER assume the VPC endpoint policy matches the IAM policy. The
  endpoint policy is an independent layer; it can deny actions that
  IAM allows. Bypass the endpoint to verify.

- NEVER assume `PrivateDnsEnabled: true` on an interface endpoint is
  cosmetic. Without it, the service's DNS name resolves to the public
  IP and traffic routes over the internet instead of the endpoint.

- NEVER conclude "the network is flaky" without running `nc -vz` or
  equivalent from the source host at least three times. Intermittent
  packet loss is rare in VPC; intermittent failures are usually
  stateful (DNS cache, connection pool, failover) not packet-loss.

- NEVER assume Transit Gateway route propagation is automatic. Each
  attachment must be associated with a TGW route table AND propagate
  its routes. Association alone does not propagate.

- NEVER assume PrivateLink endpoint service availability implies NLB
  health. The endpoint can be `available` while the NLB has no
  healthy targets in the consumer's AZ. Always check NLB target
  health.

- NEVER recommend modifying a NACL to deny specific traffic as a
  security fix without checking the existing rule order. NACLs
  evaluate lowest-to-highest rule number; first match wins. A new
  deny at rule 200 is shadowed by an existing allow at rule 100.

- NEVER recommend expanding a CIDR to `0.0.0.0/0` to "fix" a SG
  issue. This exposes the listener to the entire internet. Use the
  narrowest scope that covers the legitimate source.

- NEVER rely on Reachability Analyzer as the sole evidence. It models
  the configured state; it does not test the live packet. Pair it
  with `nc -vz` from the source host.

- NEVER skip VPC Flow Logs when diagnosing intermittent issues. Flow
  Logs with `action: REJECT` confirm the packet was dropped by SG or
  NACL; `action: ACCEPT` confirms the packet reached the ENI.

## Pre-flight safety checks (run before any state-changing CLI)

- **MANDATORY CONFIRMATION GATE.** Before any state-changing operation
  (`authorize-security-group-ingress`, `create-network-acl-entry`,
  `create-route`, `modify-vpc-endpoint`, `accept-vpc-peering-
  connection`), emit and await operator approval.

- **Read-only first.** Every probe in the diagnostic tree is
  read-only (`describe-*`, `dig`, `nc -vz`, Reachability Analyzer).
  Do not perform state-changing operations as diagnostic probes.

- **SG changes should prefer CIDR over specific IP** for tolerance to
  instance moves within the subnet, but never expand the scope to
  `0.0.0.0/0` to "fix" a connectivity issue.

- **NACL changes are not stateful.** Adding an inbound rule requires
  a matching outbound rule on the ephemeral range for the return
  traffic. Always update both directions.

- **Route table changes affect every subnet using the table.** A
  VPC-wide main route table change affects every subnet that does not
  have an explicit subnet-level table. Verify scope before applying.

- **VPC peering accept changes the accepter's network exposure.**
  Accepting a peering connection allows the requester's VPC to reach
  the accepter's VPC per the route table. Confirm the route table
  scope before accepting.

- **Transit Gateway route changes affect every attachment using the
  table.** Verify the TGW route table's association and propagation
  scope before modifying.

- **VPC endpoint policy changes affect every VPC using the endpoint.**
  Tighten gradually; never deny-by-default without confirming no
  workload depends on the denied action.

- **Bulk remediation batch limit.** If the diagnosis identifies the
  same root cause across multiple subnets/instances (e.g., a missing
  NACL outbound rule), batch remediation into groups of at most 5
  resources, emit a single CONFIRM per batch, and verify between
  batches.

## Remediation guidance

### For ROUTE_TABLE_MISSING — no route for destination

```bash
aws ec2 create-route --route-table-id <rtb> \
  --destination-cidr-block <dest-cidr> \
  --vpc-peering-connection-id <pcx>   # for peered VPC
  # --transit-gateway-id <tgw>         # for TGW
  # --gateway-id <igw-xxx>             # for internet (with public IP)
  # --nat-gateway-id <nat-xxx>         # for internet (private)
```

Verify both source and destination route tables have the corresponding
route.

### For ROUTE_TABLE_WRONG_TARGET — wrong route target

Replace the route with the correct target:

```bash
aws ec2 replace-route --route-table-id <rtb> \
  --destination-cidr-block <dest-cidr> \
  --nat-gateway-id <nat-xxx>   # or other correct target
```

### For ROUTE_OVERLAPPING_CIDR — silent peering failure

- Renumber one VPC to a non-overlapping CIDR (major change; plan a
  maintenance window).
- Or migrate connectivity to Transit Gateway with PrivateLink overlay
  (translation).

### For SG_INBOUND — missing or mis-scoped inbound rule

```bash
aws ec2 authorize-security-group-ingress --group-id <sg> \
  --protocol tcp --port <port> --cidr <source-cidr>
```
Prefer a referenced SG (same-VPC) or prefix list over a raw CIDR.
Verify with `nc -vz`.

### For SG_OUTBOUND — missing source-side egress

Same pattern, on the source SG. The default egress is allow-all; if
the egress was tightened, restore the necessary scope.

### For SG_REFERENCE_CROSS_VPC — dead SG reference

Replace the cross-VPC SG reference with:
- A CIDR block matching the source's peered-VPC subnet, OR
- A referenced SG in the peered VPC (with peering in the route table).

### For NACL_STATELESS — missing ephemeral rule

Add the inbound rule on the listener port from the source CIDR. Add
the outbound rule on the ephemeral port range (1024-65535) to the
source CIDR. Verify with `nc -vz`.

### For DNS_RESOLUTION — VPC DNS settings

```bash
aws ec2 modify-vpc-attribute --vpc-id <vpc-id> \
  --enable-dns-support
aws ec2 modify-vpc-attribute --vpc-id <vpc-id> \
  --enable-dns-hostnames
```

### For DNS_PHZ_ASSOCIATION — PHZ not associated

Associate the PHZ with the consumer VPC:

```bash
aws route53 associate-vpc-with-hosted-zone \
  --hosted-zone-id <hz-id> \
  --vpc VPCRegion=<region>,VPCId=<vpc-id>
```

For cross-account, use Shared VPC or a Route 53 Resolver Rule.

### For ENDPOINT_POLICY — endpoint policy blocking

```bash
aws ec2 modify-vpc-endpoint --vpc-endpoint-id <vpce> \
  --policy-document '<JSON with the necessary Allow>'
```

### For PEERING_INACTIVE — peering not active

Accept the peering on the accepter side:

```bash
aws ec2 accept-vpc-peering-connection \
  --vpc-peering-connection-id <pcx>
```

### For PEERING_DNS_RESOLUTION — remote DNS flag false

The flag is set at peering creation; to enable on an existing
peering:

```bash
aws ec2 modify-vpc-peering-connection-options \
  --vpc-peering-connection-id <pcx> \
  --requester-peering-connection-options \
    AllowDnsResolutionFromRemoteVpcDomainName=true
```

Both VPCs must have `enableDnsSupport` and `enableDnsHostnames` true.

### For PEERING_SG_REFERENCE — dead cross-VPC SG reference

Replace with a CIDR or a referenced SG in the peered VPC.

### For TGW_ROUTE_PROPAGATION — routes not propagating

```bash
aws ec2 enable-transit-gateway-route-table-propagation \
  --transit-gateway-route-table-id <tgw-rtb> \
  --transit-gateway-attachment-id <attachment-id>
```

### For TGW_ASSOCIATION_MISSING — attachment not associated

```bash
aws ec2 associate-transit-gateway-route-table \
  --transit-gateway-route-table-id <tgw-rtb> \
  --transit-gateway-attachment-id <attachment-id>
```

### For PRIVATELINK_ENDPOINT_SERVICE — provider-side issue

Restore the NLB and listener; verify target health in the consumer's
AZ.

### For PRIVATELINK_SG — endpoint SG missing

Add an inbound rule to the endpoint's SG:

```bash
aws ec2 authorize-security-group-ingress --group-id <endpoint-sg> \
  --protocol tcp --port <listener-port> --cidr <source-cidr>
```

## Deep reference: VPC connectivity layer model

### Layer ordering for timeout symptoms (strict OSI)

```
DNS resolution      (L7)   →  does the hostname resolve?
Routing             (L3)   →  does the route table have a route?
SG (source egress)  (L4)   →  does the source SG allow the SYN out?
SG (dest ingress)   (L4)   →  does the dest SG allow the SYN in?
NACL (source)       (L4)   →  both directions: SYN out, SYN-ACK back
NACL (dest)         (L4)   →  both directions: SYN in, SYN-ACK out
Cross-VPC plumbing  (L3)   →  peering/TGW/PrivateLink state and routes
Port reachability   (L4)   →  does nc -vz succeed?
Application         (L7)   →  TLS handshake, auth, application logic
```

Skipping a layer produces false root causes. Always probe in order.

### SG vs NACL comparison

| Property | Security Group | Network ACL |
|---|---|---|
| Stateful | Yes (return traffic automatic) | No (each direction evaluated) |
| Rule evaluation | All rules evaluated; any allow matches | Lowest rule number wins; first match |
| Default | Deny all inbound, allow all outbound | Default NACL: allow all; custom NACL: deny all |
| Applies to | ENI (instance / Lambda / NLB / endpoint) | Subnet |
| Source | CIDR, SG reference (same-VPC or peered), prefix list | CIDR only |
| Return traffic | Implicit allow | Requires explicit rule on ephemeral range |

### VPC peering vs Transit Gateway

| Property | VPC Peering | Transit Gateway |
|---|---|---|
| Topology | Point-to-point | Hub-and-spoke |
| Transitivity | No | Yes (via TGW route table) |
| Cross-region | Yes (cross-region peering) | Yes (inter-region peering via TGW) |
| Cost | Free (data transfer fees apply) | Hourly per attachment + per-GB |
| Route table | Per-VPC | Centralised on TGW |
| Overlapping CIDRs | Silent failure | Silent failure (same limit) |
| Use case | Small mesh, single-pair | Many-VPC mesh, centralised routing |

### VPC endpoint types

| Type | Services supported | Cost | Configuration |
|---|---|---|---|
| Gateway | S3, DynamoDB | Free | Route table entry; automatic prefix list |
| Interface | Most AWS services | Hourly + per-GB | ENI in subnet; SG governs |
| Gateway Load Balancer | GatewayLB (third-party firewalls) | Hourly + per-GB | Appliance-backed |

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

## Domain

AWS CloudOps / VPC Networking, Routing, Security Groups, NACLs, DNS,
Cross-VPC Connectivity (Peering, Transit Gateway, PrivateLink), and
Packet-Path Diagnostics.

## AWS documentation

- **Amazon VPC User Guide** — https://docs.aws.amazon.com/vpc/latest/userguide/
- **VPC route tables** — https://docs.aws.amazon.com/vpc/latest/userguide/VPC_Route_Tables.html
- **Security groups** — https://docs.aws.amazon.com/vpc/latest/userguide/VPC_SecurityGroups.html
- **Network ACLs** — https://docs.aws.amazon.com/vpc/latest/userguide/vpc-network-acls.html
- **VPC peering** — https://docs.aws.amazon.com/vpc/latest/peering/Welcome.html
- **Transit Gateway** — https://docs.aws.amazon.com/vpc/latest/tgw/What_is_TGW.html
- **AWS PrivateLink** — https://docs.aws.amazon.com/vpc/latest/privatelink/concepts.html
- **VPC endpoints** — https://docs.aws.amazon.com/vpc/latest/userguide/vpc-endpoints.html
- **Reachability Analyzer** — https://docs.aws.amazon.com/vpc/latest/reachability/What-is-Reachability-Analyzer.html
- **VPC Flow Logs** — https://docs.aws.amazon.com/vpc/latest/userguide/flow-logs.html
- **Route 53 Resolver** — https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/resolver.html
- **AWS Health** — https://docs.aws.amazon.com/health/latest/ug/
