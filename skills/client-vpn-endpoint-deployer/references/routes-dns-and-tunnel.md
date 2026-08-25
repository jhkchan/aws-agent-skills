# Routes, DNS, and Tunnel Mode — Client VPN Endpoint Deployer

Deep reference on Client VPN route tables (propagated vs static
routes, route-to-authorization-rule dependency), DNS configuration
(custom DNS servers, split-tunnel DNS leak prevention, VPC DNS
resolver), split-tunnel vs full-tunnel trade-offs, transport protocol
selection, subnet association concurrency limits, and CloudWatch
metrics. Loaded on demand by the skill — kept out of the main SKILL.md
body so the provisioning procedure stays scannable.

## Route tables

### Propagated routes (automatic)

When a subnet is associated with a Client VPN endpoint, AWS
automatically creates a propagated route for the VPC's CIDR. This
enables connected clients to reach resources within the associated
VPC without manual route configuration.

```bash
# Verify propagated routes
aws ec2 describe-client-vpn-routes \
  --client-vpn-endpoint-id cvpn-xxx \
  --query 'Routes[?Type==`propagated`]' \
  --region us-east-1 --output table
```

### Static routes (manual)

For CIDRs BEYOND the VPC (peered VPCs, on-premises via TGW/DX, the
internet), add static routes pointing to a target subnet association:

```bash
aws ec2 create-client-vpn-endpoint-route \
  --client-vpn-endpoint-id cvpn-xxx \
  --destination-cidr 172.16.0.0/16 \
  --target-vpc-subnet-id subnet-aaa11122 \
  --region us-east-1
```

**A static route without an authorization rule is unreachable.** Each
destination CIDR must also have a corresponding authorization rule:

```bash
# Route for peered VPC
aws ec2 create-client-vpn-endpoint-route \
  --client-vpn-endpoint-id cvpn-xxx \
  --destination-cidr 172.16.0.0/16 \
  --target-vpc-subnet-id subnet-aaa11122

# Authorization rule for peered VPC (REQUIRED)
aws ec2 authorize-client-vpn-ingress \
  --client-vpn-endpoint-id cvpn-xxx \
  --target-network-cidr 172.16.0.0/16 \
  --authorize-all-groups
```

### Internet access via NAT Gateway

For connected clients to access the internet through the VPC (full-
tunnel or explicit internet route):

```bash
# Route 0.0.0.0/0 to a subnet with a NAT Gateway
aws ec2 create-client-vpn-endpoint-route \
  --client-vpn-endpoint-id cvpn-xxx \
  --destination-cidr 0.0.0.0/0 \
  --target-vpc-subnet-id subnet-public-with-nat

# Authorization rule for internet
aws ec2 authorize-client-vpn-ingress \
  --client-vpn-endpoint-id cvpn-xxx \
  --target-network-cidr 0.0.0.0/0 \
  --authorize-all-groups
```

## DNS configuration

### VPC DNS resolver

The Amazon-provided DNS server for a VPC is at the `.2` address of
the VPC CIDR. For a `10.0.0.0/16` VPC, it is `10.0.0.2`. This
resolver:

- Resolves VPC private DNS hostnames (e.g., `ip-10-0-1-5.ec2.internal`).
- Forwards to the Route 53 Resolver for private hosted zones.
- Forwards public DNS queries to public DNS servers.

### Custom DNS servers

Push custom DNS servers to connected clients via the endpoint config:

```bash
aws ec2 modify-client-vpn-endpoint \
  --client-vpn-endpoint-id cvpn-xxx \
  --dns-servers 10.0.0.2 \
  --region us-east-1
```

For multiple DNS servers:

```bash
--dns-servers 10.0.0.2,10.0.0.200
```

### Split-tunnel DNS leak

With `SplitTunnel=true`, only traffic destined for the VPC CIDR (or
pushed routes) goes through the VPN. DNS queries follow the client's
local resolver unless custom DNS servers are pushed.

```text
WITHOUT custom DNS in split-tunnel:
  Client queries ip-10-0-1-5.ec2.internal
    → Client local resolver (e.g., 192.168.1.1 or 8.8.8.8)
    → NXDOMAIN (local resolver does not know VPC DNS)
    → VPC hostname resolution FAILS

WITH custom DNS (10.0.0.2) in split-tunnel:
  Client queries ip-10-0-1-5.ec2.internal
    → VPN tunnel pushes DNS server 10.0.0.2
    → Query goes through tunnel to VPC DNS resolver
    → Resolves to 10.0.1.5 ✓
```

**Always set custom DNS servers when using split-tunnel.** The VPC
DNS resolver (`.2` address) is the recommended value.

## Split-tunnel vs full-tunnel

### Split-tunnel

Traffic for the VPC CIDR + pushed routes goes through the VPN. All
other traffic uses the client's local network.

**Advantages:**
- Lower bandwidth consumption on the VPN endpoint.
- Lower AWS egress costs (user internet traffic does not go through
  AWS NAT Gateway).
- Better performance for non-VPC traffic.

**Disadvantages:**
- Requires custom DNS servers to prevent DNS leaks.
- Less secure (user's local internet traffic is not inspected by
  corporate security tools).

### Full-tunnel

ALL client traffic goes through the VPN, including internet traffic.

**Advantages:**
- All traffic inspected by corporate security tools (firewalls, IDS).
- No DNS leak risk (DNS goes through the tunnel).
- Simpler configuration (no custom DNS servers needed).

**Disadvantages:**
- Higher AWS egress costs (all user internet traffic goes through AWS
  NAT Gateway).
- Higher latency for user internet traffic.
- More bandwidth consumption on the VPN endpoint.

### When to use each

| Use case | Recommended mode |
|---|---|
| Corporate VPN for office workers | Split-tunnel (custom DNS set) |
| Security-sensitive environments (finance, healthcare) | Full-tunnel |
| Developer access to VPC resources | Split-tunnel (custom DNS set) |
| Compliance requiring all-traffic inspection | Full-tunnel |
| Cost-sensitive environments | Split-tunnel (lower egress cost) |

## Transport protocol

| Protocol | Port | Pros | Cons |
|---|---|---|---|
| UDP | 443 | Lower latency, faster connection setup | May be blocked by restrictive firewalls |
| TCP | 443 | Works through restrictive firewalls/proxies | Higher latency, slower setup |
| TCP | 1194 | Alternative if 443 is blocked | Less common, may be blocked |

**Recommendation:** start with UDP on 443 (default). If users report
connection failures from restrictive networks (hotels, conference
Wi-Fi), switch to TCP on 443 or provision a second endpoint with TCP.

## Subnet association concurrency

AWS processes subnet associations sequentially within an endpoint. If
you create multiple associations concurrently, some may fail with
`ClientVpnEndpointAssociationLimitExceeded`.

**Correct pattern (sequential):**

```bash
# Associate subnet 1
aws ec2 create-client-vpn-endpoint-target-network-association \
  --client-vpn-endpoint-id cvpn-xxx \
  --subnet-id subnet-aaa11122 \
  --region us-east-1

# Wait for association to become available
aws ec2 describe-client-vpn-target-networks \
  --client-vpn-endpoint-ids cvpn-xxx \
  --query 'ClientVpnTargetNetworks[?TargetNetworkId==`subnet-aaa11122`].Status.Code' \
  --region us-east-1 --output text
# Wait until output is "available"

# THEN associate subnet 2
aws ec2 create-client-vpn-endpoint-target-network-association \
  --client-vpn-endpoint-id cvpn-xxx \
  --subnet-id subnet-bbb22233 \
  --region us-east-1
```

**Maximum:** 12 associations per endpoint (soft limit; request
increase via AWS Support).

## CloudWatch metrics

Client VPN publishes metrics under `AWS/ClientVPN` namespace with the
dimension `Endpoint=<cvpn-id>`.

### Key metrics

| Metric | Description | Alert threshold |
|---|---|---|
| `ActiveConnections` | Current active connections | Track baseline; alert on sudden drop |
| `AuthenticationFailures` | Failed authentication count | Alert on spike (possible attack) |
| `ConnectionSetupDuration` | Time to establish connection | Alert if > 10s average |
| `EgressBytes` / `IngressBytes` | Throughput | Track for capacity planning |
| `EgressPackets` / `IngressPackets` | Packet counts | Track for capacity planning |

### CloudWatch alarm for authentication failures

```bash
aws cloudwatch put-metric-alarm \
  --alarm-name "vpn-auth-failures" \
  --namespace AWS/ClientVPN \
  --metric-name AuthenticationFailures \
  --dimensions Name=Endpoint,Value=cvpn-xxx \
  --statistic Sum \
  --period 300 \
  --threshold 10 \
  --comparison-operator GreaterThanThreshold \
  --evaluation-periods 1 \
  --alarm-actions arn:aws:sns:us-east-1:123456789012:vpn-alerts \
  --region us-east-1
```

## Common pitfalls

1. **No authorization rule created.** Clients connect but cannot reach
   any IP. Always create at least one `authorize-client-vpn-ingress`
   rule.

2. **Split-tunnel without custom DNS.** VPC hostname resolution fails.
   Always set `DnsServers` to the VPC `.2` resolver.

3. **Client CIDR overlaps VPC CIDR.** Routing ambiguity causes
   connection failures. Use a dedicated RFC1918 range that does not
   overlap any target VPC.

4. **Static route without authorization rule.** The route is
   unreachable. Each destination CIDR needs BOTH a route AND an
   authorization rule.

5. **Concurrent subnet associations fail.** AWS processes
   associations sequentially. Wait for each to reach `available`
   before creating the next.

## Expert heuristic: split-tunnel DNS leak prevention

Split-tunnel routes only VPC-relevant traffic through the VPN. Without
custom DNS servers, clients use their local resolver for DNS queries —
including queries for VPC private hostnames — which fail.

```text
Split-tunnel with NO custom DNS (BROKEN):
  Client → DNS query for ip-10-0-1-5.ec2.internal
    → Local resolver (8.8.8.8) → NXDOMAIN → fails

Split-tunnel WITH custom DNS (CORRECT):
  Endpoint config: DnsServers = ["10.0.0.2"]  (VPC .2 resolver)
  Client → DNS query → VPN tunnel → VPC DNS resolver → resolves ✓

Full-tunnel (no DNS leak risk):
  All traffic including DNS goes through tunnel → no custom DNS needed
  Downside: all internet traffic egresses via AWS (cost)
```

**Key implication:** when `SplitTunnel=true`, always set
`DnsServers=["<VPC-DNS-resolver>"]` (the VPC CIDR `.2` address).
