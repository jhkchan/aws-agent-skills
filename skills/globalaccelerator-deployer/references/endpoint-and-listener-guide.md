# Endpoints, Listeners, and Endpoint Groups Reference

Supplementary reference for the Global Accelerator Deployer skill.
Use when planning endpoint types, listener protocols, endpoint group
topology, traffic dials vs endpoint weights, or health check tuning.

## Listener protocols and port ranges

| Protocol | Use case | Notes |
|---|---|---|
| `TCP` | HTTPS, HTTP/2, HTTP/3 (TCP), SSH, custom TCP | Reliable delivery. Most common. |
| `UDP` | QUIC, VoIP (RTP/UDP), gaming (UDP), DNS-over-UDP | No delivery guarantee. Per-flow load balancing. |
| `TCP_UDP` | Same port on both protocols (DNS on 53) | Listener accepts both; endpoints receive matching protocol. |

**Port range constraints:**
- Each range: 1-65535 inclusive.
- Up to 10 port ranges per listener.
- Ranges are inclusive (`FromPort` to `ToPort`).
- Custom routing listeners allocate sub-ranges per endpoint deterministically.

## Client affinity

| Setting | Behavior | When to use |
|---|---|---|
| `NONE` (default) | Sticky per-flow. Each new flow (TCP connection, UDP session) is load-balanced independently. | Stateless HTTP, API, CDN origins. |
| `SOURCE_IP` | Sticky per source IP for the affinity window (~30 seconds). All flows from one client IP go to the same endpoint during the window. | Gaming sessions, long-lived streams, stateful backends. |

**Anti-pattern:** NEVER set `SOURCE_IP` for stateless HTTP — it defeats
load balancing, pins users to one endpoint, and creates hot shards
when a NAT or CDN sits in front of many users who all appear as one
source IP.

## Endpoint group topology

An endpoint group is **region-scoped**: one group covers one AWS
region. Within a listener, you create one endpoint group per region
you want to route to.

```
Accelerator
  └─ Listener (TCP/443)
       ├─ Endpoint group: us-east-1 (traffic dial 100)
       │    ├─ ALB endpoint (weight 128)
       │    └─ ALB endpoint (weight 128)
       ├─ Endpoint group: eu-west-1 (traffic dial 100)
       │    └─ ALB endpoint (weight 256)
       └─ Endpoint group: ap-southeast-1 (traffic dial 50)
            └─ ALB endpoint (weight 256)
```

**Traffic dial vs endpoint weight:**
- **Traffic dial** (0-100): per-region, per-group. What percentage of
  GLOBAL traffic this region gets (relative to other groups).
- **Endpoint weight** (0-999): per-endpoint within a group. How this
  group's traffic is split across its endpoints.

To shift traffic between regions, change traffic dials. To shift
traffic between endpoints in the same region, change endpoint weights.

## Endpoint types and homogeneity rule

| Type | ARN shape | Default client IP |
|---|---|---|
| ALB | `arn:aws:elasticloadbalancing:<region>:<acct>:loadbalancer/app/<name>/<id>` | Via `X-Forwarded-For` (always) |
| NLB | `arn:aws:elasticloadbalancing:<region>:<acct>:loadbalancer/net/<name>/<id>` | Configurable via `PreserveClientIpEnabled` |
| EC2 | `i-0123456789abcdef0` (instance ID) | Configurable via `PreserveClientIpEnabled` |
| Elastic IP | `eipalloc-0123456789abcdef0` (allocation ID) | Preserved at L4 by definition |

**Homogeneity rule:** within one endpoint group, all endpoints MUST be
the same type. `AddEndpoints` returns `ValidationError` if you mix
ALB with NLB, NLB with EC2, etc. Multi-type designs require separate
endpoint groups (in different regions, by definition).

## Health check configuration

| Field | Default | Range | Notes |
|---|---|---|---|
| `HealthCheckIntervalSeconds` | 30 | 10 or 30 | 10s for latency-sensitive (higher cost); 30s for general. |
| `HealthCheckPath` | `/` | string | Required for HTTP/HTTPS; ignored for TCP. |
| `HealthCheckPort` | listener port | 1-65535 | Can differ from listener port. |
| `HealthCheckProtocol` | listener protocol | TCP, HTTP, HTTPS | ALB: uses the target group health check (override not supported). |
| `ThresholdCount` | 3 | 1-10 | Consecutive failed checks before unhealthy. Lower = faster failover, more flapping. |

**ALB exception:** for ALB endpoints, Global Accelerator uses the ALB's
own target group health check. The `HealthCheckProtocol`, `Path`, and
`Port` fields on the endpoint group are ignored for ALB endpoints.

## Traffic dial behavior in detail

| Dial value | Behavior |
|---|---|
| 100 | Full traffic to this region (default for active-active). |
| 50 | Half-weight relative to peer regions (canary, blue-green). |
| 5 | Minimal traffic (drain candidate; leave at 5 until connections close). |
| 0 | Hard cut. New flows stop immediately; existing flows MAY be dropped. |

**Drain pattern (recommended):**
1. Reduce traffic dial from 100 → 5 (or set endpoint weight to 0).
2. Monitor flow logs or origin connection count for 5-10 minutes.
3. Once connections drop to baseline, set traffic dial to 0.
4. Verify via `list-endpoint-groups` that no new flows are routed.

## Endpoint weight behavior in detail

| Weight value | Behavior |
|---|---|
| 0 | Graceful drain. No new connections; existing stay until close. |
| 1-999 | Relative weight within the group. 128 is a common default. |
| equal weights | Even split across all endpoints in the group. |

Weight is **relative**, not absolute. If endpoint A=128 and B=64, A
gets 128/(128+64) = 2/3 of the group's traffic. Weights of 128 and
256 produce the same 1:2 ratio as 64 and 128.

## BYOIP flow (for reference; provisioning is out of scope of this skill)

1. **ROA publication** (RIR-side): publish a Route Origin Authorization
   with your RIR (ARIN, RIPE, APNIC) authorizing AS16509 (Amazon) to
   advertise your CIDR. Validation takes hours to days.
2. **Route 53 provisioning** (account-side): generate a signed message
   using your RIR's API key, then call
   `aws ec2 provision-byoip-cidr --cidr <CIDR> --cidr-authorization-context ...`.
   Move to `PROVISIONED` state (minutes to hours).
3. **Advertising** (GA-side): on `create-accelerator`, pass
   `--byoip-cidrs <CIDR>`. GA advertises the CIDR from all AWS edges.
4. **Move between accelerators** (optional): de-advertise (delete
   accelerator or update to remove BYOIP), then re-advertise on a new
   accelerator.

**State machine:**
```
(deleted) → PENDING_PROVISIONING → PROVISIONED → (advertised via GA)
                                      ↓
                              FAILED_PROVISIONING (rare; ROA/signature issue)
```

Only `PROVISIONED` CIDRs can be advertised via GA. Verify with
`aws ec2 describe-byoip-cidrs` before passing to `create-accelerator`.

## Custom routing accelerator port mapping

In a standard accelerator, the listener port maps to the same port
on all endpoints. In a custom routing accelerator, GA allocates a
**deterministic sub-range** of the listener's port range per endpoint.

```
Listener port range: 10000-10999 (1000 ports)
Endpoint A: listener ports 10000-10099 → destination port 27015
Endpoint B: listener ports 10100-10199 → destination port 27016
Endpoint C: listener ports 10200-10299 → destination port 27017
...
```

The matchmaker queries `list-custom-routing-port-mappings` to discover
the allocation and assigns each player a unique listener port. The
player connects to that listener port and is routed deterministically
to one endpoint:destination-port combination.

**Constraints:**
- No health checks (caller's responsibility to verify endpoint readiness).
- No traffic dial (the port allocation IS the routing).
- No client IP preservation toggle (always preserved at L4 by definition).
- Destination protocols: `TCP`, `UDP`, or both per endpoint.
