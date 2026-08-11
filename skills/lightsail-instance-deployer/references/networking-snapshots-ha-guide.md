# Networking, Snapshots, and HA Reference

Supplementary reference for the Lightsail Instance Deployer skill.
Use when configuring static IPs, DNS zones, VPC peering, snapshots,
load balancers, or designing HA patterns.

## Static IP lifecycle

A Lightsail static IP is a fixed public IPv4 address that you can
attach to one instance. The IP is yours until you release it.

```
[allocate-static-ip] → detached ($0.005/hr billable)
       ↓
[attach-static-ip] → attached to instance (free)
       ↓
[detach-static-ip] → detached again ($0.005/hr billable)
       ↓
[release-static-ip] → IP returned to AWS pool (no further billing)
```

**Billing rule:** the static IP is free ONLY while attached to a
running instance. Detached (orphan) static IPs cost $0.005/hour
(~$3.60/month). Always `release-static-ip` when an instance is
deleted.

**One-to-one rule:** a static IP attaches to one instance only. For
a shared entry point across multiple instances, use a Lightsail load
balancer (the LB has its own DNS name; instances sit behind it).

**Stop/start behavior:** the static IP stays attached through stop/
start cycles. Without a static IP, the public IP changes on stop/start
— DNS A records silently break.

## DNS zones and records

A Lightsail DNS zone is a managed Route 53 hosted zone scoped to
Lightsail. It is a separate resource from Route 53 hosted zones you
create via the Route 53 API/Console.

**To use a Lightsail DNS zone:**
1. Create the zone: `aws lightsail create-dnszone --domain-name example.com`.
2. AWS assigns 4 nameservers (e.g., `ns-123.awsdns.com`, ...).
3. At your registrar (GoDaddy, Namecheap, etc.), set the domain's
   nameservers to the Lightsail-assigned ones.
4. Wait for DNS propagation (minutes to hours).
5. Create records: A, AAAA, CNAME, MX, TXT, NS, SOA, PTR.

**Record examples:**

```bash
# A record: app.example.com → static IP
aws lightsail create-domain-entry --domain-name example.com \
  --domain-entry '{"name":"app","type":"A","target":"192.0.2.10"}'

# CNAME: www.example.com → app.example.com
aws lightsail create-domain-entry --domain-name example.com \
  --domain-entry '{"name":"www","type":"CNAME","target":"app.example.com"}'

# MX: example.com → mail handler
aws lightsail create-domain-entry --domain-name example.com \
  --domain-entry '{"name":"@","type":"MX","target":"10 mail.example.com"}'
```

**Limits:**
- 5 DNS zones per account (soft limit).
- No hard cap on records per zone.
- Zone apex must be A or AAAA (not CNAME).

**Anti-pattern:** NEVER create a DNS A record before attaching the
static IP. If you create the A record first, you must update it
after attachment — the record points to the wrong IP until you do.

## VPC peering — Lightsail VPC to default EC2-VPC

Lightsail runs in a per-region managed VPC (typically
`172.26.0.0/16`, but verify). The default EC2-VPC is a separate VPC
(typically `172.31.0.0/16`). Without peering, the two are isolated.

**Enable peering (per region):**

```bash
aws lightsail is-vpc-peered --region us-east-1   # check first
aws lightsail peer-vpc --region us-east-1         # enable
```

After peering, the Lightsail instance can reach (one-way: Lightsail →
EC2-VPC):
- RDS instances in the default VPC (by private IP or RDS endpoint).
- ElastiCache nodes in the default VPC.
- EC2 instances in the default VPC (private IP).
- VPC endpoints (interface, gateway) in the default VPC.

**RDS security group:** allow inbound from the Lightsail VPC CIDR
(verify via `aws ec2 describe-vpc-peering-connections`). The RDS
instance must be in the default VPC. For RDS in a non-default VPC,
use a transit gateway or a manual VPC peering connection between the
Lightsail VPC and the non-default VPC (Lightsail does not expose its
VPC for manual peering; the `peer-vpc` API only peers to the default).

**Verification after peering:**

```bash
aws lightsail is-vpc-peered --region us-east-1   # should return true
aws ec2 describe-vpc-peering-connections --region us-east-1 \
  --filters Name=status,Values=active
```

From the Lightsail instance:

```bash
# Test RDS reachability
nc -zv db-private.xxxxxxx.us-east-1.rds.amazonaws.com 3306
# Expected: Connection to ... port 3306 [tcp/mysql] succeeded!
```

**Anti-pattern:** NEVER assume Lightsail can reach RDS without
peering. The #1 surprise for teams migrating from EC2 is that the
Lightsail instance cannot reach RDS until `peer-vpc` is enabled.

## Snapshots — automatic and manual

### Automatic snapshots

```bash
aws lightsail enable-add-on --resource-name prod-instance \
  --add-on-request '{"addOnType":"AutoSnapshot","snapshotTimeOfDay":"05:00","status":"Active"}'
```

- `snapshotTimeOfDay`: UTC HH:00 (e.g., `05:00`, `17:00`). Daily schedule.
- Retention: 7 days default; configurable 1-365 via the Lightsail console.
- Cost: ~$0.05/GB-month (billed for the snapshot storage).
- Includes system disk + attached block disks.

### Manual snapshots

```bash
aws lightsail create-instance-snapshot --instance-snapshot-name prod-pre-update-2026-08-07 \
  --instance-name prod-instance
```

- Persist until explicitly deleted.
- Cost: same ~$0.05/GB-month.
- Use for: pre-update rollback, cloning, DR baselines.

### Restore from snapshot

```bash
aws lightsail create-instances-from-snapshot --instance-name prod-instance-restored \
  --availability-zone us-east-1a --bundle-id medium_3_0 \
  --instance-snapshot-name prod-pre-update-2026-08-07
```

The restored instance is a new instance (new public IP unless you
attach the original static IP, new private IP). Attach the static IP
from the original instance to the restored one to preserve DNS.

### Snapshot best practices

- Enable automatic snapshots on every production instance.
- Take a manual snapshot before any application or OS update.
- Review retention monthly — large bundles (320-640 GB SSD) accrue
  significant snapshot storage cost.
- Test restore quarterly — an untested snapshot is a hope, not a plan.

## Lightsail load balancer (Layer 4)

```bash
aws lightsail create-load-balancer --load-balancer-name prod-lb \
  --instance-port 80 --health-check-path / \
  --region us-east-1
aws lightsail attach-instances-to-load-balancer --load-balancer-name prod-lb \
  --instance-names prod-instance-1 prod-instance-2
```

| Capability | Support |
|---|---|
| Layer | Layer 4 (TCP / TCP+TLS) |
| TLS termination | Yes (ACM-managed certificate) |
| Health check | Path-based HTTP/HTTPS |
| Sticky sessions | Duration-based (1-60 min) |
| Path-based routing | NOT supported |
| Host-based routing | NOT supported |
| HTTP/2 server push | NOT supported |
| WebSocket | Supported (TCP passthrough) |
| Cross-zone load balancing | Supported (default) |

For Layer 7 features, deploy an ALB in EC2-VPC (reachable from
Lightsail via VPC peering). The Lightsail instance targets the ALB;
the ALB does path/host routing to multiple target groups.

### HA pattern with Lightsail LB

```
Internet
   ↓
Lightsail LB (TLS on 443)
   ↓                    ↓
Instance 1 (us-east-1a)  Instance 2 (us-east-1b)
   ↓                    ↓
Multi-AZ Lightsail Database (primary us-east-1a, standby us-east-1b)
```

**Health check:** path `/` (or `/healthz` for app-specific checks),
interval 10 sec, healthy threshold 2, unhealthy threshold 2.

**Sticky sessions:** enable for session-based apps (WordPress,
Django with file-based sessions). Duration 1 hour typical; adjust
to your session lifetime.

## Lightsail distribution (CDN)

A Lightsail distribution is a CloudFront-backed CDN scoped to
Lightsail origins. It supports cache behaviors, TLS via ACM, and
origin protocol policies.

```bash
aws lightsail create-distribution --distribution-name prod-cdn \
  --origin '{"name":"prod-static-site","region":"us-east-1","protocolPolicy":"http-only"}' \
  --default-cache-behavior '{"behavior":"cache"}'
```

| Aspect | Lightsail Distribution | CloudFront (proper) |
|---|---|---|
| Origin scope | Lightsail instance or Lightsail bucket | Any HTTP origin (S3, ALB, EC2, on-prem) |
| Cache behaviors | Limited | Full (path patterns, lambda triggers) |
| TLS | ACM-managed | ACM-managed (must be us-east-1) |
| WAF | Not supported directly | WAFv2 association |
| Pricing | Lightsail-bundled | Per-GB + per-request |

Use a Lightsail distribution when the origin is a Lightsail instance
or bucket and you want simple cache management. Use CloudFront proper
when you need WAF, Lambda@Edge, multi-origin failover, or non-Lightsail
origins.

## Multi-AZ Lightsail database

```bash
aws lightsail create-relational-database \
  --relational-database-name prod-db \
  --relational-database-blueprint-id mysql_8_0 \
  --relational-database-bundle-id medium_3_0 \
  --master-username admin \
  --master-user-password '<strong-password>' \
  --availability-zone us-east-1a \
  --secondary-availability-zone us-east-1b \
  --publicly-accessible false
```

- **Primary** in `availability-zone`; **standby** in `secondary-availability-zone`.
- Standby takes over on primary failure (60-120 seconds).
- Connection string points to the managed endpoint — no client-side failover.
- Multi-AZ doubles the cost vs. single-AZ.
- `publicly-accessible: false` keeps the DB private (recommended).

**Best practices:**
- Always set `publicly-accessible: false` for production.
- Reach the DB via VPC-peered Lightsail instances by private IP.
- Use the managed endpoint in connection strings; do NOT hardcode the
  primary AZ IP — it changes on failover.
- Take manual snapshots before schema migrations; automatic snapshots
  may not capture the pre-migration state.
