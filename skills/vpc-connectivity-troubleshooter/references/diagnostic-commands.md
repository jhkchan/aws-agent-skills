# Diagnostic Commands — VPC Connectivity Troubleshooter

Pre-flight, per-step probe, and diagnostic command listings moved out of the SKILL.md body. Loaded on demand.

## Pre-flight commands (source/destination context and AWS Health gate)

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

## Step 2: Connection timeout — OSI-aligned diagnostic tree (2a-2j)

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

## Step 3: DNS resolution failure (3a-3c)

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

## Step 4: VPC endpoint policy

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

## Step 5: VPC peering — Active but traffic times out (5a-5e)

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

## Step 6: Transit Gateway — attachments Active but traffic times out (6a-6c)

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

## Step 7: PrivateLink — endpoint accepted but service unreachable (7a-7d)

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

## Step 8: Application layer — TLS / auth

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

## Step 9: Escalate or NEED_MORE_INFO

If none of the above produced a positive root-cause match, OR the
symptom clearly indicates an AWS-side incident (AZ-wide degradation,
region event, Direct Connect carrier issue), emit one of:

- **ESCALATE** — AWS-side incident. Surface the AWS Health event ARN
  and recommend opening a Support case. Do NOT continue diagnosing.
- **NEED_MORE_INFO** — A specific probe requires operator input. List
  the missing pieces (source instance ID, destination identifier,
  port, protocol, region) and the next probe to run once the info is
  available.
