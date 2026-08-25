# Advanced Patterns — Global Accelerator Deployer

Expert-knowledge deep dives, edge-case catalogs, common patterns, and recent AWS features moved verbatim from SKILL.md for progressive disclosure. Load on demand.

### Step 0: Expert knowledge — non-obvious Global Accelerator behaviors that change the plan (moved from SKILL.md)

- **The two static IPs are anycast and pinned for the accelerator's
  lifetime.** They cannot be re-mapped without deletion + recreation.
  For migrations, plan DNS TTL tuning and dual-running windows. BYOIP
  ranges give portability — move a BYOIP range between accelerators by
  de-advertising and re-advertising.

- **Endpoint groups are region-scoped.** One endpoint group covers one
  AWS region. Traffic dials are per group (per region), NOT per
  endpoint. Within a group, endpoints are weighted. To shift traffic
  between regions, change traffic dials; to shift between endpoints in
  the same region, change endpoint weights.

- **Traffic dial 0 drops ALL traffic to the region.** It is NOT
  "drain" — it is a hard cut, and existing flows may be dropped. For
  graceful drain, reduce to 5, wait for connections to close (verify
  via flow logs), then 0. Endpoint weight 0 within a group IS graceful
  drain (no new connections, existing stay until close).

- **Mixing endpoint types in one endpoint group is rejected by the
  API.** `AddEndpoints` with an ALB ARN into an NLB group returns
  `ValidationError`. Multi-type designs require separate endpoint
  groups, each in a different region.

- **Client IP preservation differs by endpoint type.** ALB endpoints
  always see the client IP via `X-Forwarded-For` (the L4 source IP at
  the ALB is an AWS GA IP). NLB and EC2 endpoints can set
  `PreserveClientIpEnabled: true` — the L4 source IP at the origin IS
  the client IP. Preservation ON = origin SG must allow client IP
  ranges; OFF = origin SG scopes to the GA prefix pool
  (`51.224.0.0/14` for IPv4, 2026).

- **BYOIP requires Route 53 provisioning BEFORE advertising.** Flow:
  (1) publish ROA with your RIR, (2) provision the CIDR in Route 53
  via `ec2 provision-byoip-cidr` (signed message), (3) wait for
  `PROVISIONED` state, (4) advertise via GA on accelerator creation.
  Skipping step 2 makes the CIDR unusable — GA cannot advertise a
  CIDR not provisioned in your account.

- **Custom routing accelerators expose endpoint-specific ports.** In a
  standard accelerator, the listener port maps to the same port on all
  endpoints. In a custom routing accelerator, GA allocates a
  deterministic range of listener ports per endpoint — a client
  connecting to listener port 10042 reaches a specific
  endpoint:destination-port combination. Use for gaming, VoIP, media.

- **Health check protocol must match the endpoint.** ALB: uses the
  ALB's target group health check. NLB: TCP, HTTP, or HTTPS,
  independently of the NLB's own target group check. EC2: TCP or
  HTTP/HTTPS; the EC2 instance must have a listener on the health
  check port.

- **Flow log destination policy is critical.** CloudWatch: GA uses the
  `AWSServiceRoleForGlobalAccelerator` service-linked role with
  `logs:CreateLogStream` and `logs:PutLogEvents`. S3: bucket policy
  MUST grant `s3:PutObject` to `flowlogs.globalaccelerator.amazonaws.com`.
  A misconfigured destination silently drops flow logs — there is no
  error surfaced in accelerator status.

- **Dual-stack requires accelerator recreation.** IPv6 support (Nov
  2023) is set at accelerator creation. An accelerator created before
  that date cannot be updated to dual-stack — create a new accelerator
  and migrate DNS.

### Step 7: Cross-account endpoints (2024+) — RAM resource share (moved from SKILL.md)

Cross-account endpoints centralize the accelerator in one account
(the "network"/"edge" account) while endpoints live in workload
accounts. Use cases: shared edge platform, multi-tenant SaaS,
separation of networking from application ownership.

**Resource owner account:**

```bash
aws ram create-resource-share --name prod-alb-share \
  --resource-arns "arn:aws:elasticloadbalancing:us-east-1:222222222222:loadbalancer/app/prod-alb/abc"
aws ram associate-resource-share --resource-share-arn <rs-arn> --principals "111111111111"
```

**Consumer account (accept invitation):**

```bash
aws ram accept-resource-share-invitation --resource-share-invitation-arn <invitation-arn>
```

**Verify share is ACTIVE before adding endpoint:**
`aws ram get-resource-shares --resource-arns <endpoint-arn>`. The
endpoint ARN in `add-endpoints` uses the consumer-account ARN; GA
resolves it via the RAM share. If the share is `PENDING` or
`REJECTED`, `add-endpoints` returns `AccessDeniedException`.

### Step 8: Custom routing accelerator — deterministic port mapping (moved from SKILL.md)

```bash
aws globalaccelerator create-custom-routing-accelerator --name prod-gaming-ga --ip-addresses IPV4
aws globalaccelerator create-custom-routing-listener --accelerator-arn <arn> \
  --port-ranges "FromPort=10000,ToPort=10999"
aws globalaccelerator create-custom-routing-endpoint-group --listener-arn <arn> \
  --endpoint-group-region us-east-1 \
  --destination-configurations '[{"EndpointId":"i-0abc","Protocols":["TCP","UDP"],"DestinationPorts":[{"FromPort":27015,"ToPort":27015}]}]'
```

GA allocates listener ports deterministically: each endpoint gets a
sub-range of the listener's port range. A client connecting to
listener port 10042 is routed to a specific endpoint:destination-port
combination. Use `list-custom-routing-port-mappings` to discover the
allocation.

**Custom routing constraints:**
- No health checks (assumes endpoint readiness).
- No traffic dial (the listener port allocation IS the routing).
- Destination protocols: `TCP`, `UDP`, or both.
- No client IP preservation config (always preserved at L4 by definition).

## Common patterns (moved from SKILL.md)

- **Multi-region ALB active-active.** Two regional ALBs (us-east-1 +
  eu-west-1), each in its own endpoint group, both traffic dial 100.
  Anycast routing sends each user to the closest region. Client IP at
  origin via `X-Forwarded-For`. Use for global SaaS frontends.

- **Single-region NLB with client IP preservation.** NLB endpoint with
  `PreserveClientIpEnabled: true`. Origin sees real client IP for rate
  limiting and geo-blocking. Use for gaming backends, financial APIs.

- **Custom routing for gaming.** Custom routing accelerator, listener
  port range 10000-19999. Each game server EC2 is an endpoint with
  destination ports matching the per-session range. Matchmaker queries
  `list-custom-routing-port-mappings` to assign each player a port.

- **Cross-account centralized edge.** Accelerator in the "network"
  account; endpoints are ALBs in workload accounts. RAM resource share
  for each ALB. Network team owns accelerator and IP reputation (BYOIP);
  workload teams own the ALB and target groups.

## Recent AWS features (2024-2026) (moved from SKILL.md)

- **Cross-account endpoints (2024):** endpoints in peer AWS accounts,
  shared via RAM resource share. Enables centralized edge platform
  with distributed workload ownership. Requires `ACTIVE` share before
  `add-endpoints`.

- **Custom routing accelerators (2023-2024):** deterministic port-to-
  endpoint mapping for gaming, VoIP, and media workloads. Listener
  port range allocated to endpoints via `list-custom-routing-port-mappings`.
  No traffic dial or health checks — caller's responsibility.

- **Dual-stack IPv4+IPv6 (2023):** accelerators created after Nov 2023
  can be dual-stack (IPv4 + IPv6 anycast IPs). Older accelerators must
  be recreated and DNS migrated.

- **BYOIP for Global Accelerator (2022-2024):** advertise your own
  /24+ IPv4 CIDR through GA. Requires ROA + Route 53 provisioning
  (`PROVISIONED` state). Enables IP portability across accelerators.

- **Flow logs to S3 (2023):** GA flow logs can stream to S3 in addition
  to CloudWatch Logs. Useful for long-term retention and Athena queries.
  Bucket policy MUST grant `s3:PutObject` to the GA logging principal.

- **Health check enhancements (2024-2025):** per-endpoint health check
  override — different intervals per endpoint within a group.

- **Endpoint weight drain (2025):** weight 0 is now documented as
  graceful drain. Traffic dial 0 remains a hard cut.

