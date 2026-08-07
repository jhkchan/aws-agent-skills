# VPC Connectivity Layer Reference Guide

Supplementary reference for the VPC Connectivity Troubleshooter skill.
Loaded on-demand when a diagnostic needs port/protocol semantics,
SG/NACL evaluation rules, peering / TGW / PrivateLink specifics, or
Reachability Analyzer / Flow Logs usage patterns.

## Common application ports

| Application | Default port | Protocol | Notes |
|---|---|---|---|
| HTTP | 80 | TCP | Web frontends, ALB listener |
| HTTPS | 443 | TCP | TLS web frontends |
| SSH | 22 | TCP | EC2 admin (lock down source CIDR) |
| RDP | 3389 | TCP | Windows admin |
| PostgreSQL | 5432 | TCP | RDS Postgres / Aurora PG |
| MySQL | 3306 | TCP | RDS MySQL / Aurora MySQL |
| Microsoft SQL Server | 1433 | TCP | RDS SQL Server |
| Oracle | 1521 | TCP | RDS Oracle (TNS listener) |
| Redis | 6379 | TCP | ElastiCache Redis |
| Memcached | 11211 | TCP | ElastiCache Memcached |
| MongoDB | 27017 | TCP | DocumentDB (MongoDB-compatible) |
| Kafka | 9092, 9094 | TCP | MSK (9094 for TLS) |
| Elasticsearch | 443 | TCP | OpenSearch (HTTPS) |
| DNS | 53 | TCP/UDP | Route 53 Resolver |
| NTP | 123 | UDP | Time sync |
| SMTP | 25, 587, 465 | TCP | SES endpoints |

Custom ports: SG rules and NACLs MUST reference the actual port the
listener is bound to. Operators who copy-paste a default-port rule
into a custom-port listener silently drop traffic.

## Ephemeral port range

When a client connects to a server on a well-known port, the client's
source port is a random ephemeral port. The return packet uses the
ephemeral port as destination.

| OS / runtime | Default ephemeral range |
|---|---|
| Linux (modern kernels) | 32768-60999 |
| Windows Server | 49152-65535 |
| macOS | 49152-65535 |
| AWS Lambda (managed) | 1024-65535 (varies) |

For NACL design, the safe range is 1024-65535 (covers all common OSes).
NACL outbound rules on the listener side MUST allow the ephemeral range
back to the client CIDR for the SYN-ACK to deliver.

## SG vs NACL comparison

| Property | Security Group | Network ACL |
|---|---|---|
| Stateful | Yes (return traffic automatic) | No (each direction evaluated) |
| Rule evaluation | All rules evaluated; any allow matches | Lowest rule number wins; first match |
| Default (newly created) | Deny all inbound, allow all outbound | Deny all inbound AND outbound (custom NACL) |
| Default (VPC default NACL) | n/a | Allow all in and out |
| Applies to | ENI (instance / Lambda / NLB / endpoint) | Subnet |
| Source/destination | CIDR, SG reference (same-VPC or peered), prefix list | CIDR only |
| Return traffic | Implicit allow | Requires explicit rule on ephemeral range |
| Order of operations | After routing, before NACL | Before routing decision on inbound (subnet-bound); after SG on outbound |

NACLs are evaluated on entry to and exit from the SUBNET. SGs are
evaluated on entry to and exit from the ENI. For a packet flowing
source-ENI → source-subnet → network → dest-subnet → dest-ENI, the
evaluation order is:

```
source-ENI SG egress →
  source-subnet NACL egress (stateless) →
    network (route tables, peering, TGW) →
      dest-subnet NACL ingress (stateless) →
        dest-ENI SG ingress
```

The return SYN-ACK follows the reverse path, with stateless NACLs
re-evaluated independently.

## VPC peering reference

### Status codes

| Status | Effect |
|---|---|
| `initiating-request` | Requester is creating the peering; ephemeral. |
| `pending-acceptance` | Request sent; accepter must accept. No traffic flows. |
| `active` | Peering up; traffic flows per route tables and SGs. |
| `rejected` | Accepter explicitly rejected. No traffic flows. |
| `expired` | Accepter did not accept within 7 days. No traffic flows. |
| `failed` | AWS could not establish the peering (e.g., overlapping CIDRs detected at accept time). |
| `provisioning` | Peering is being established after acceptance. |
| `deleting`, `deleted` | Peering torn down. |

### Limitations

- **Not transitive.** A-B peering + B-C peering does NOT allow A → C.
- **No overlapping CIDRs.** Both VPCs must have non-overlapping CIDRs.
- **One peering per VPC pair.** Cannot create a second peering between
  the same two VPCs.
- **Same-region and cross-region supported.** Cross-region peering does
  not require TGW.
- **Inter-region VPC peering data transfer fees apply** in both
  directions.

### DNS resolution across peering

For DNS hostnames in the peer VPC to resolve:
- Both VPCs must have `enableDnsSupport: true` AND
  `enableDnsHostnames: true`.
- The requester side must enable
  `AllowDnsResolutionFromRemoteVpcDomainName: true` at peering
  creation time (or via `modify-vpc-peering-connection-options`).
- This flag is one-way; each side controls its own VPC's DNS exposure.

## Transit Gateway reference

### Attachment types

| Attachment type | What it connects |
|---|---|
| `vpc` | A VPC (one attachment per VPC) |
| `vpn` | Site-to-Site VPN |
| `direct-connect-gateway` | Direct Connect gateway |
| `connect` | Connect attachment (SD-WAN) |
| `peering` | Inter-region TGW peering |

### TGW route table concepts

- **Association:** the TGW route table the attachment is "in" (one per
  attachment). Determines which routes the attachment SEES.
- **Propagation:** whether the attachment's VPC CIDR is automatically
  added to a TGW route table. An attachment can propagate to multiple
  tables.
- **Default association route table:** set on the TGW; new attachments
  are auto-associated with this table.
- **Default propagation route table:** set on the TGW; new attachments
  auto-propagate to this table.

Common TGW failures:
- Attachment associated but not propagating → attachment's CIDR is
  invisible to other attachments.
- Two attachments associated with different TGW route tables → they
  cannot reach each other unless static routes exist.

### TGW vs VPC peering

| Property | VPC Peering | Transit Gateway |
|---|---|---|
| Topology | Point-to-point | Hub-and-spoke |
| Transitivity | No | Yes |
| Cross-region | Yes (cross-region peering) | Yes (inter-region peering via TGW) |
| Cost | Free (data transfer fees apply) | Hourly per attachment + per-GB |
| Route table | Per-VPC | Centralised on TGW |
| Overlapping CIDRs | Silent failure | Silent failure (same limit) |
| Use case | Small mesh, single-pair | Many-VPC mesh, centralised routing, VPN/DX |

## AWS PrivateLink reference

### Components

| Component | Side | Purpose |
|---|---|---|
| Endpoint Service | Provider | The published service; backed by an NLB |
| Network Load Balancer | Provider | Distributes traffic to provider targets |
| Interface Endpoint | Consumer | ENI in the consumer VPC subnet |
| Endpoint SG | Consumer | Inbound rules on the endpoint ENI |

### Endpoint states

| State | Effect |
|---|---|
| `pending-waiting` | Provider must accept (if `AcceptanceRequired: true`) |
| `pending-acceptance` | Provider is reviewing |
| `available` | Endpoint is up; traffic flows per SG and NLB |
| `rejected` | Provider explicitly rejected |
| `failed` | NLB deleted or unavailable |
| `deleted` | Endpoint torn down |

### Private DNS

`PrivateDnsEnabled: true` (default) makes the service's base DNS name
(e.g., `service.region.amazonaws.com`) resolve to the endpoint's
private IP from within the consumer VPC. `false` requires the consumer
to use the endpoint-specific DNS name or IP.

Operators who set `PrivateDnsEnabled: false` to "avoid conflict" with
an existing public record see traffic route over the internet instead
of the endpoint.

### Common PrivateLink failures

- Endpoint SG does not allow the source.
- Endpoint service NLB has no healthy targets in the consumer's AZ.
- Provider deleted the NLB; endpoint transitions to `failed`.
- Consumer's `PrivateDnsEnabled` does not match the consumer's DNS
  configuration; the service DNS name resolves to the public IP.

## VPC endpoint policy reference

A VPC endpoint policy is a JSON document attached to the endpoint. It
is independent of IAM and is evaluated in addition to IAM (both must
allow the action).

For Gateway endpoints (S3, DynamoDB): the policy is at the endpoint
level. Each VPC route table with the endpoint's prefix list applies
the policy.

For Interface endpoints: the policy is at the endpoint level. Each
endpoint ENI applies the policy.

### Common restrictive patterns

- Allow `s3:GetObject` only on a specific bucket → blocks
  `s3:PutObject` even with IAM allow.
- Allow principals from a specific account only → blocks cross-account
  principals even with IAM allow.
- Allow only `aws:SourceVpce` matching this endpoint → blocks traffic
  not coming through the endpoint (forces all VPC traffic through the
  endpoint).

### Bypass test

To verify the endpoint policy is the cause:
- For Gateway endpoints: temporarily route via a subnet without the
  endpoint's prefix list.
- For Interface endpoints: temporarily route via NAT Gateway or a
  different endpoint.

If the API call succeeds when bypassing the endpoint, the endpoint
policy is the cause.

## Reachability Analyzer usage

Reachability Analyzer models the VPC network path between a source and
destination and reports whether traffic would flow, plus the
explanations for any block.

### Create and run

```bash
PATH_ID=$(aws ec2 create-network-insights-path \
  --source <source-eni-id> \
  --destination <dest-eni-id> \
  --destination-port <port> \
  --protocol tcp \
  --output json | jq -r '.NetworkInsightsPath.NetworkInsightsPathId')

ANALYSIS_ID=$(aws ec2 start-network-insights-analysis \
  --network-insights-path-id $PATH_ID \
  --output json | jq -r '.NetworkInsightsAnalysis.NetworkInsightsAnalysisId')

# Wait for Status: succeeded
aws ec2 describe-network-insights-analyses \
  --network-insights-analysis-ids $ANALYSIS_ID --output json | \
  jq '.NetworkInsightsAnalyses[0] | {Status, ForwardPathComponents,
    Explanations}'
```

### Explanations

The `Explanations` field lists why traffic would not flow, with one of:

| Explanation code | Meaning |
|---|---|
| `ENI_SG_RULE_MISSING` | Source / dest SG rule missing |
| `NACL_RULE_MISSING` | NACL rule missing in either direction |
| `ROUTE_TABLE_MISSING` | Route table entry missing |
| `PEERING_CONNECTION_MISSING` | VPC peering not present or not Active |
| `TRANSIT_GATEWAY_ATTACHMENT_MISSING` | TGW attachment missing or non-Active |
| `TRANSIT_GATEWAY_ROUTE_MISSING` | TGW route table missing route |
| `DESTINATION_PORT_CLOSED` | Destination port not listening |
| `INTERNET_GATEWAY_MISSING` | IGW missing for internet-routed traffic |
| `NAT_GATEWAY_MISSING` | NAT missing for private-subnet internet egress |

Pair Reachability Analyzer with `nc -vz` for confirmation: Reachability
Analyzer models configured state; `nc -vz` tests live packet behaviour.

## VPC Flow Logs usage

VPC Flow Logs capture metadata about IP traffic going to/from network
interfaces in a VPC. They are not packet captures — they are flow
records (srcAddr, dstAddr, srcPort, dstPort, protocol, bytesPackets,
action).

### Action codes

| Action | Meaning |
|---|---|
| `ACCEPT` | Packet reached the ENI (or left the ENI on egress). Does NOT confirm the application received it. |
| `REJECT` | Packet was dropped by a SG or NACL. The specific SG / NACL is identified by location. |

### Querying Flow Logs (CloudWatch Logs Insights)

```text
fields @timestamp, srcAddr, dstAddr, srcPort, dstPort, protocol, action
| filter (srcAddr = "<source-ip>" and dstAddr = "<dest-ip>" and dstPort = <port>)
  or (srcAddr = "<dest-ip>" and dstAddr = "<source-ip>" and srcPort = <port>)
| sort @timestamp desc
| limit 50
```

For Athena-backed Flow Logs, use a partitioned table and Athena SQL
queries for long-running analysis.

### Limitations

- Flow Logs do NOT capture packet payload.
- Flow Logs are aggregated over a capture window (default 60 seconds
  for `accept`, 60 seconds for `reject`). Sub-second bursts may
  aggregate.
- Flow Logs are eventually consistent — there is a delay (1-5 minutes)
  between packet observation and log delivery.
- Flow Logs at the VPC level capture every ENI; at the subnet or ENI
  level they capture only that scope. Verify the scope before
  concluding "no traffic reached the destination" from a subnet-level
  log.

## DNS reference

### VPC DNS settings

| Setting | Effect |
|---|---|
| `enableDnsSupport: true` | The VPC's .2 address (AmazonProvidedDNS) is a DNS resolver. Required for any AWS DNS resolution. |
| `enableDnsSupport: false` | The VPC's .2 address is not a resolver. PHZ, private hostnames, and Resolver rules do not work. |
| `enableDnsHostnames: true` | The VPC can have private DNS hostnames (e.g., `ec2-10-0-1-10.us-east-1.compute.internal`). Required for PHZ. |
| `enableDnsHostnames: false` | The VPC cannot have private DNS hostnames. |

Both must be true for Route 53 private hosted zones to resolve.

### Route 53 Resolver components

| Component | Purpose |
|---|---|
| Resolver Inbound Endpoint | Forwards DNS queries FROM on-prem / external TO the VPC resolver |
| Resolver Outbound Endpoint | Forwards DNS queries FROM the VPC TO an external resolver (e.g., on-prem) |
| Resolver Rule | Specifies a domain and how to handle it (SYSTEM uses AWS resolver; FORWARD sends to a target; RECURSIVE recursively resolves) |

### PHZ cross-account patterns

| Pattern | Use |
|---|---|
| Same-account PHZ + same-account VPC | `associate-vpc-with-hosted-zone` |
| Cross-account PHZ + consumer VPC | Use AWS RAM (Resource Access Manager) to share the PHZ, OR use a Resolver FORWARD rule from the consumer VPC to the PHZ owner's inbound endpoint |
| PHZ + peered VPC | The PHZ must be associated with the consumer VPC directly; peering does NOT propagate PHZ associations |

## AWS Health event categories that affect VPC connectivity

| Category | Likely impact |
|---|---|
| `AWS_EC2_INSTANCE` | Specific instance degradation; not a network issue |
| `AWS_EC2_INSTANCE_AZ` | AZ-wide EC2 degradation; affects instances in one AZ |
| `AWS_VPC` | VPC service degradation; rare, but reachability checks may fail |
| `AWS_DIRECTCONNECT` | Direct Connect circuit issue; on-prem paths affected |
| `AWS_VPN` | Site-to-Site VPN issue; on-prem paths affected |
| `AWS_REGIONAL_EVENT` | Region-wide; multiple services affected |
| `AWS_ROUTE53_DNS` | Route 53 DNS resolution degradation |

Always probe `aws health describe-events` for regional issues before
declaring a customer-side root cause during a wide-impact incident.
