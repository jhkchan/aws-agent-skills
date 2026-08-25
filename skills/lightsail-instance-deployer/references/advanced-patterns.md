# Advanced patterns — lightsail-instance-deployer

Expert-knowledge deep dives, optional-component details, and edge cases moved verbatim from SKILL.md for progressive disclosure. Load on demand.

## Step 0: Expert knowledge — non-obvious Lightsail behaviors that change the plan

- **Lightsail lives in its own VPC, isolated from EC2-VPC.** To reach
  RDS, ElastiCache, or private EC2 in the default EC2-VPC, you MUST
  enable VPC peering via `aws lightsail peer-vpc --region <region>`.
  The peering is one-way (Lightsail → EC2-VPC) and per-region. Verify
  with `aws lightsail is-vpc-peered --region <region>`.

- **Static IPs are billed when detached.** Attached to a running
  instance: free. Detached (orphan): $0.005/hour (~$3.60/month). Orphan
  static IPs are a common cost leak — delete unused with
  `release-static-ip`.

- **App+OS blueprints bundle the application stack with vendor
  defaults.** WordPress ships with WordPress + Apache + MySQL + PHP
  pre-installed. The default admin password is generated at launch and
  surfaced in the launch output — capture it immediately; not
  retrievable after the session. Use OS-only with `apt install` for a
  non-default stack.

- **Bundles include data transfer — overage is metered.** Outbound to
  internet is included up to the allowance (1 TB on small plans, up
  to 8 TB on the largest). Inbound is always free. Overage ~$0.09/GB.
  Lightsail-to-Lightsail in-region is free; cross-region is metered.

- **Stop/start changes the public IP unless a static IP is attached.**
  DNS A records pointing to the non-static IP silently break. ALWAYS
  attach a static IP before configuring DNS A records.

- **Snapshots include the system disk AND attached block disks.**
  Automatic snapshots run on schedule (daily or weekly) and retain
  the latest N days (default 7, configurable 1-365). New instances
  can be created from snapshots (`create-instances-from-snapshot`).

- **Lightsail load balancers are Layer 4 (TCP/TLS) only.** No
  path-based routing, host-based routing, or HTTP/2 server push. For
  Layer 7 features, use an ALB in EC2-VPC (reachable via VPC peering).

- **Lightsail distributions are CloudFront-backed but scoped to
  Lightsail origins.** Can front a Lightsail instance or bucket. Cannot
  directly front an arbitrary EC2 instance or S3 in another account —
  those require CloudFront proper. Trade-off: simpler management vs.
  flexibility.

- **Multi-AZ databases have a primary + standby in different AZs.**
  Standby takes over on primary failure (60-120 sec). Connection string
  points to the managed endpoint — no client-side failover. Multi-AZ
  doubles the cost vs. single-AZ.

- **Firewall rules are per-port, per-protocol, per-source.** Default
  allows 22, 80, 443 from anywhere. Tighten by CIDR (e.g., 22 from
  corporate range only). Stateful — outbound response traffic is
  allowed regardless of inbound rules.

## Step 7: Snapshots — automatic and manual

**Automatic snapshots:**

```bash
aws lightsail enable-add-on --resource-name prod-instance \
  --add-on-request '{"addOnType":"AutoSnapshot","snapshotTimeOfDay":"05:00","status":"Active"}'
```

`snapshotTimeOfDay` is UTC HH:00. Retention defaults to 7 days
(configurable 1-365). Automatic snapshots billed at ~$0.05/GB-month.

**Manual snapshot (pre-deploy or pre-update):**

```bash
aws lightsail create-instance-snapshot --instance-snapshot-name prod-pre-update-2026-08-07 \
  --instance-name prod-instance
```

Manual snapshots persist until explicitly deleted. Use for pre-update
rollback, cloning, and DR baselines. New instances can be created from
snapshots via `create-instances-from-snapshot` (clone or DR).

## Step 8: Lightsail load balancer (Layer 4 TCP/TLS)

```bash
aws lightsail create-load-balancer --load-balancer-name prod-lb \
  --instance-port 80 --health-check-path / --region us-east-1
aws lightsail attach-instances-to-load-balancer --load-balancer-name prod-lb \
  --instance-names prod-instance-1 prod-instance-2
```

Lightsail LBs are Layer 4: TCP or TCP+TLS. Support health checks
(path-based HTTP/HTTPS), sticky sessions (duration-based), and TLS
(ACM-managed). They do NOT support path-based/host-based routing or
HTTP/2 server push. For Layer 7, use an ALB in EC2-VPC.

**HA pattern:** 2+ instances in different AZs behind one Lightsail LB.
Sticky sessions (duration-based) keep a user on the same instance —
required for session-based apps.

## Step 9: Container services (optional)

```bash
aws lightsail create-container-service --service-name prod-container \
  --power nano --scale 1 --region us-east-1
aws lightsail create-container-service-deployment --service-name prod-container \
  --containers '{"app":{"image":"nginx:latest","ports":{"80":"HTTP"}}}' \
  --public-endpoint '{"containerName":"app","containerPort":80,"healthCheck":{"healthyThreshold":2,"intervalSeconds":10}}'
```

Managed ECS-like platform: images from ECR or public registries,
automatic TLS, public endpoint (load balancer), scale 1-N. Power
levels: `nano`, `micro`, `small`, `medium`, `large`. Use for
containerized apps that don't need a full EC2/ECS cluster.

## Step 10: Lightsail distribution (CDN, optional)

```bash
aws lightsail create-distribution --distribution-name prod-cdn \
  --origin {"name":"prod-instance","region":"us-east-1","protocolPolicy":"http-only"} \
  --default-cache-behavior '{"behavior":"cache"}' \
  --region us-east-1
```

A Lightsail distribution is a CloudFront-backed CDN scoped to
Lightsail origins (instance or bucket). It supports cache behaviors,
TLS via ACM, and origin protocol policies. Use to front a static site
or media-heavy instance; offload cacheable content to the edge and
reduce instance load.

**Limitations vs. CloudFront proper:** distributions only support
Lightsail instance or Lightsail bucket origins (no arbitrary S3, ALB,
or on-prem). For those, use CloudFront proper.

## Step 11: Lightsail database (optional, multi-AZ for HA)

```bash
aws lightsail create-relational-database \
  --relational-database-name prod-db \
  --relational-database-blueprint-id mysql_8_0 \
  --relational-database-bundle-id medium_3_0 \
  --master-username admin \
  --master-user-password '<strong-password>' \
  --availability-zone us-east-1a \
  --secondary-availability-zone us-east-1b \
  --publicly-accessible false \
  --region us-east-1
```

Multi-AZ databases have a primary in `availability-zone` and a standby
in `secondary-availability-zone`. The standby takes over on primary
failure (60-120 seconds). Connection string points to the managed
endpoint — no client-side failover logic. Multi-AZ doubles the cost
vs. single-AZ.

`publicly-accessible false` keeps the database private — reachable
only from peered Lightsail instances or EC2-VPC resources. NEVER set
`publicly-accessible true` for production databases — it exposes the
DB to the internet.

## Expert heuristic: choosing bundle (plan) for workload type

The "right" bundle is a function of workload type, expected traffic,
and budget. The heuristic below resolves the trade-off.

| Workload | Minimum bundle | Recommended | Reason |
|---|---|---|---|
| Static site / blog (low traffic) | `nano_3_0` (512 MB) | `micro_3_0` (1 GB) | Nginx/Apache idles under 200 MB; headroom for traffic spikes. |
| WordPress (app+OS) | `medium_3_0` (4 GB) | `large_3_0` (8 GB) | WordPress minimum is `medium_3_0`. PHP-FPM + MySQL under load needs 4+ GB. |
| LAMP / Node.js app (app+OS) | `medium_3_0` (4 GB) | `large_3_0` (8 GB) | App+OS minimum is `medium_3_0`. Add RAM for concurrent workers. |
| Custom OS-only app | `micro_3_0` (1 GB) | `small_3_0` (2 GB) | Custom stack: tune to the app's memory profile. |
| Production web/API (multi-instance) | `small_3_0` (2 GB) per instance | `medium_3_0` (4 GB) per instance | HA across 2+ instances; smaller bundle per instance is OK because load is distributed. |
| Database (single-AZ) | `small_3_0` (2 GB) | `medium_3_0` (4 GB) | MySQL/PostgreSQL benefits from RAM for buffer pool. |
| Database (multi-AZ HA) | `small_3_0` (2 GB) | `medium_3_0` (4 GB) | Same as single-AZ; cost doubles for the standby. |
| Container service | `nano` power | `small` power | Container power is a separate scale (nano/micro/small/medium/large). |

**Decision rules:**
- For app+OS blueprints, NEVER go below the vendor minimum (typically
  `medium_3_0`, 4 GB). Smaller bundles install but fail under load.
- For OS-only with a custom stack, profile RAM at peak and add 50%
  headroom. CPU scales linearly with bundle size.
- For HA, prefer 2x `medium_3_0` behind a Lightsail LB over 1x
  `xlarge_3_0`. The HA pair survives AZ failure; the single large
  instance does not.
- Data transfer: monitor outbound. Near the allowance? Add a Lightsail
  distribution (CDN) to offload cacheable content.
- Snapshots billed at ~$0.05/GB-month. A `medium_3_0` snapshot (80 GB)
  is ~$4/month; a `2xlarge_3_0` (640 GB) is ~$32/month — review
  retention carefully.

ALWAYS emit the bundle choice as a PRE_CHECKS row naming the workload
type, selected bundle, and rationale (vendor minimum, headroom, HA).

## Recent AWS features (2024-2026)

- **Multi-AZ Lightsail databases (2024):** primary + standby in
  different AZs with automatic failover (60-120 sec). Managed
  endpoint; no client-side failover. Doubles the cost vs. single-AZ.
- **Lightsail distributions (2023-2024):** CloudFront-backed CDN scoped
  to Lightsail origins (instance or bucket). Simpler than CloudFront
  proper; cannot front arbitrary S3/ALB origins.
- **Lightsail object storage buckets (2023):** S3-compatible buckets
  managed via the Lightsail API/Console. Useful for static assets,
  backups, media; frontable by a distribution.
- **Container services (2022-2024):** managed ECS-like platform.
  Images from ECR or public registries, automatic TLS, public
  endpoint, scale 1-N. Power: nano/micro/small/medium/large.
- **Amazon Linux 2023 blueprint (2023-2024):** latest Amazon Linux AMI
  as a Lightsail OS-only blueprint. Replaces Amazon Linux 2.
- **Block storage disks (2024):** attach additional block disks to an
  instance for more storage without upgrading the bundle. Snapshots
  include attached block disks.
