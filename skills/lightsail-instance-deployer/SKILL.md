---
name: lightsail-instance-deployer
description: 'Provisions production-grade Amazon Lightsail instances with secure defaults: blueprint selection (OS-only vs app+OS bundle), bundle (plan) sizing for CPU/RAM/SSD/transfer, static IP attachment, DNS via Lightsail DNS zones, VPC peering to the default EC2-VPC for private access to RDS/ElastiCache, automatic and manual snapshots, Lightsail load balancers (Layer 4 with TLS), container services, Lightsail distributions (CloudFront-backed CDN), and multi-AZ managed databases. Emits a deployment plan with a READY_TO_DEPLOY checklist. Use when provisioning a new Lightsail instance, attaching a static IP, configuring a DNS zone, peering to EC2-VPC for private resource access, setting up snapshots, deploying a Lightsail load balancer, creating a container service, fronting an instance with a distribution, or provisioning a multi-AZ Lightsail database.'
license: Apache-2.0
compatibility: Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). No AWS CLI required for offline architecture planning. Live deployment uses aws lightsail create-instances, create-instance-snapshot, create-disk-from-snapshot, attach-static-ip, create-load-balancer, create-container-service, create-distribution, create-relational-database, enable-add-on (automatic snapshots), create-dnszone, is-vpc-peered, peer-vpc, and aws ec2 describe-vpc-peering-connections (AWS CLI v2...
metadata:
  domain: aws-cloudops
  complexity: medium
  requires_llm: 'true'
  phase: '1'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: Compute
  task_type: deploy
  skill_class: capability
  lifecycle_status: active
  verdict_shape: READY_TO_DEPLOY | PREREQUISITES_MISSING
  when_to_use: Provisioning a new Lightsail instance for production, attaching a static IP for stable DNS, configuring a Lightsail DNS zone, peering the Lightsail VPC to the default EC2-VPC for private access to RDS or ElastiCache, configuring automatic and manual snapshots, deploying a Lightsail load balancer for HA, creating a container service, fronting an instance with a Lightsail distribution (CDN), or provisioning a multi-AZ managed database.
  activation_triggers: create a Lightsail instance, provision a Lightsail instance with static IP, Lightsail blueprint selection, Lightsail bundle plan sizing, Lightsail DNS zone, Lightsail VPC peering to EC2-VPC, Lightsail RDS private access, Lightsail automatic snapshots, Lightsail load balancer, Lightsail container service, Lightsail distribution CDN, Lightsail multi-AZ database, WordPress on Lightsail
  invocation_schema: 'Input shape (one of): (a) a deployment specification including blueprint (OS-only or app+OS), bundle (plan), availability zone, static IP requirement, DNS zone, VPC peering requirement, snapshot schedule, load balancer, container service, distribution, and database requirements; (b) a partial spec for interactive refinement (e.g., "WordPress on Lightsail with a static IP and daily snapshots"); (c) an existing instance name for architecture review against the well-architected checklist. Output shape: { INSTANCE_SPEC, VERDICT, ARCHITECTURE, CHECKLIST[], FINDINGS[], DEPLOY_COMMANDS } where VERDICT ∈ { READY_TO_DEPLOY, PREREQUISITES_MISSING }.'
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  keywords: Lightsail, instance deploy, blueprint, bundle, plan, OS-only, app blueprint, WordPress, LAMP, Node.js, static IP, DNS zone, VPC peering, EC2-VPC peering, private access, RDS private, snapshot, automatic snapshot, manual snapshot, load balancer, container service, Lightsail distribution, CDN, multi-AZ database, Lightsail database, availability zone, user data, cloud-init, SSH key, firewall
  tags: lightsail, compute, deploy, static-ip, dns, vpc-peering, snapshot, load-balancer, container, distribution, database
---

# Lightsail Instance Deployer

## What this skill does

Provisions production-grade Amazon Lightsail instances with secure
defaults: blueprint selection (OS-only vs app+OS bundle), bundle
(plan) sizing, static IP attachment, DNS via Lightsail DNS zones, VPC
peering to the default EC2-VPC for private access to RDS/ElastiCache,
automatic and manual snapshots, Lightsail load balancers, container
services, Lightsail distributions (CloudFront-backed CDN), and
multi-AZ managed databases. Emits a deployment plan with a
READY_TO_DEPLOY checklist.

## Mindset

**One-line takeaway:** Lightsail is **not** "a toy EC2" — it is a
**bundled compute platform** with predictable pricing that includes
the instance, a fixed-GB SSD, a monthly data-transfer allowance, and
managed add-ons (snapshots, load balancers, DNS, distributions). The
bundle is the unit of economics; the VPC peering toggle is the unit
of network reach; the static IP is the unit of DNS stability.

Three facts make Lightsail provisioning different from "give me a
small EC2":

- **Lightsail lives in its own VPC, isolated from the default EC2-VPC.**
  Without VPC peering, a Lightsail instance CANNOT reach RDS,
  ElastiCache, or any resource in the customer's default EC2-VPC. This
  is the #1 surprise for teams migrating from EC2. The peering toggle
  (`peer-vpc`) is per-region, one-way (Lightsail → EC2-VPC).

- **The bundle includes data transfer — overage is metered.** Each
  bundle includes a monthly outbound transfer allowance (1 TB on
  small plans, up to 8 TB on the largest). Inbound is always free.
  Overage ~$0.09/GB. Static IP attachment is free while attached but
  billed ($0.005/hour) when detached — orphan IPs are a common cost leak.

- **App+OS blueprints (WordPress, LAMP, Node.js) bundle the application
  stack.** A WordPress blueprint ships with WordPress, Apache, MySQL,
  and PHP pre-installed. This is NOT the same as OS-only with
  `apt install wordpress`. Use app+OS when you want the bundled stack
  with vendor defaults; use OS-only when you need full control.

## Quick navigation

| Section | What it covers | When to read it |
|---|---|---|
| **Quick reference** | Verdict thresholds + checklist matrix + Lightsail limits | Before any operation |
| **Pre-flight** | Instance metadata gate — blueprint, bundle, AZ, SSH key, peering | Before executing any CLI |
| **Process** | Per-step planning: instance, static IP, DNS, peering, snapshots, LB, container, distribution, database | When choosing each step |
| **Common patterns** | LAMP+static IP / WordPress+LB HA / RDS private access / container service | Boilerplate lookup |
| **STRICT output contract** | Required INSTANCE/VERDICT/PRE_CHECKS/STEPS/POST_VERIFY block | Formatting the response |
| **NEVER (top 5)** | Hard rules preventing common insecure patterns | Review before deploy |
| **Expert heuristic** | Choosing bundle (plan) for workload type | Choosing bundle size |

## Quick reference — verdict thresholds

| Verdict | Trigger condition | Action |
|---|---|---|
| `PREREQUISITES_MISSING` | Any pre-check failed (blueprint not found in the selected region, bundle unavailable in region, AZ does not exist in region, SSH key region mismatch, app+OS blueprint requires a minimum bundle the spec doesn't meet, VPC peering requested but EC2-VPC has no default VPC, multi-AZ database primary AZ mismatch, distribution origin unreachable, IAM permission missing, instance name collision) | List failures, do NOT execute |
| `READY_TO_DEPLOY` | All pre-checks passed; awaiting CONFIRM gate | Emit exact CLI sequence with full instance config, wait for operator yes |

**Deployment checklist (every dimension must pass):** Blueprint (OS-only
or app+OS) — Step 1; Bundle sizing (CPU/RAM/SSD/transfer; app+OS minimum)
— Step 2; AZ valid in region — Step 3; Static IP attached before DNS —
Step 4; DNS zone + A record to static IP — Step 5; VPC peering enabled
if RDS/ElastiCache access needed — Step 6; Snapshots (automatic +
manual) — Step 7; Load balancer for HA (optional) — Step 8; Container
service (optional) — Step 9; Distribution/CDN (optional) — Step 10;
Database (optional; multi-AZ for HA) — Step 11; Firewall (22/80/443
defaults, tightened per CIDR) — Step 12; User data (cloud-init,
optional) — Step 13; SSH key (default or custom) — Step 14.

**Lightsail limits (2026):**

- Bundles per region: 1 of each size (soft limit; default 5-20).
- Static IPs per region: 5 (soft limit).
- DNS zones per account: 5 (soft limit). DNS records per zone: no hard cap.
- Snapshots: depends on storage; no fixed count cap.
- Load balancers / container services / distributions per region: 5 each (soft).
- Databases per region: varies by engine (15 default for MySQL).
- Instance name: 255 chars, alphanumeric + hyphen. User data size: 16 KB.
- Availability Zones: 2-6 per region (Lightsail may not support all EC2 AZs).
- Availability Zones: 2-6 per region ( Lightsail may not support all EC2 AZs in a region).

## Pre-flight: deployment specification gate (run before architecture output)

Before producing the deployment plan, validate the input specification.
Several requirements **block deployment** — proceeding with an invalid
spec produces a non-functional or insecure instance.

**Live-account pre-flight checks (skip if doing offline architecture plan):**

1. Verify IAM permissions: `lightsail:CreateInstances`,
   `CreateInstanceSnapshot`, `AttachStaticIp`, `AllocateStaticIp`,
   `CreateLoadBalancer`, `CreateContainerService`, `CreateDistribution`,
   `CreateRelationalDatabase`, `EnableAddOn`, `CreateDnszone`,
   `PeerVpc`, `IsVpcPeered`. For peering also
   `ec2:DescribeVpcPeeringConnections`.
2. Verify the blueprint exists: `aws lightsail get-blueprints --region <region>`
   returns the blueprint ID (OS-only: `amazon_linux_2023`, `ubuntu_22_04`;
   app+OS: `wordpress`, `lamp_8`, `node_js`).
3. Verify the bundle exists and meets the app+OS minimum (if applicable):
   `aws lightsail get-bundles --region <region>`. WordPress requires
   `medium_3_0` (4 GB RAM, 2 CPU, 80 GB SSD) minimum.
4. Verify the AZ exists: `aws lightsail get-regions --include-availability-zones`.
   Lightsail may not support all EC2 AZs in a region.
5. Verify the SSH default key: `aws lightsail download-default-key-pair --region <region>`.
6. For VPC peering, verify the default EC2-VPC exists:
   `aws ec2 describe-vpcs --filters Name=isDefault,Values=true`.
7. For multi-AZ databases, verify the primary and standby AZs are both
   supported by Lightsail in the region.

| Attribute | Value | Effect on plan |
|---|---|---|
| Blueprint | OS-only (Amazon Linux 2023, Ubuntu, Debian) | Bare OS; install app stack via user data. |
| Blueprint | App+OS (WordPress, LAMP, Node.js) | Bundled stack with vendor defaults. May require minimum bundle. |
| Bundle | `nano_3_0` (512 MB, 1 CPU, 20 GB SSD, 1 TB transfer) | Cheapest; dev/test only. Not for app+OS. |
| Bundle | `medium_3_0` (4 GB, 2 CPU, 80 GB SSD, 4 TB transfer) | Minimum for most app+OS blueprints. |
| Bundle | `xlarge_3_0` (16 GB, 8 CPU, 320 GB SSD, 7 TB transfer) | Production workloads. |
| Static IP | required | Attach before DNS A record; free while attached. |
| VPC peering | required | `peer-vpc` per region; enables private RDS/ElastiCache access. |
| Multi-AZ DB | required | Primary + standby AZ; automatic failover. |

**If the deployment spec is incomplete** (missing blueprint, bundle,
or region), output:

```text
INSTANCE_SPEC: <name-or-unknown>
VERDICT: PREREQUISITES_MISSING
REASON: Deployment specification is missing required fields (<list>).
Cannot produce an instance plan without <field> — the resulting
deployment would be non-functional or insecure.
REQUIRED:
  - blueprint_id (OS-only or app+OS blueprint)
  - bundle_id (plan: CPU/RAM/SSD/transfer)
  - availability_zone (valid AZ in the selected region)
  - static_ip_required (true/false)
  - vpc_peering_required (true/false)
  - snapshot_schedule (none/daily/weekly)
```

## Process — Architecture planning (apply in order, produce deployment plan)

### Step 0: Expert knowledge — non-obvious Lightsail behaviors that change the plan

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

### Step 1: Blueprint selection

```bash
aws lightsail get-blueprints --region us-east-1
```

| Blueprint type | Examples | Use case |
|---|---|---|
| OS-only | `amazon_linux_2023`, `ubuntu_22_04`, `debian_12`, `open_suse_15`, `freebsd_12` | Custom application stack installed via user data or post-launch. |
| App+OS | `wordpress`, `wordpress_multisite`, `lamp_8`, `node_js`, `django`, `rails`, `ghost`, `joomla`, `magento`, `redmine`, `gitlab` | Bundled stack with vendor defaults. Faster launch; less control. |
| App+OS (certificate) | `nginx_plesk`, `cpanel_whm` | Web hosting control panels. License required. |

**Decision rule:** use app+OS when you want the bundled stack and the
vendor's defaults; use OS-only when you need a non-default stack,
custom package versions, or a stack the app+OS catalog doesn't offer.

### Step 2: Bundle (plan) sizing

```bash
aws lightsail get-bundles --region us-east-1
```

| Bundle ID | RAM | CPU | SSD | Transfer | $/mo | Typical use |
|---|---|---|---|---|---|---|
| `nano_3_0` | 512 MB | 1 | 20 GB | 1 TB | $3.50 | Dev/test only. Not for app+OS. |
| `micro_3_0` | 1 GB | 2 | 40 GB | 2 TB | $5 | Small app, low-traffic blog. |
| `small_3_0` | 2 GB | 2 | 60 GB | 3 TB | $10 | Small production app. |
| `medium_3_0` | 4 GB | 2 | 80 GB | 4 TB | $20 | WordPress / app+OS minimum. |
| `large_3_0` | 8 GB | 4 | 160 GB | 5 TB | $40 | Mid-tier production. |
| `xlarge_3_0` | 16 GB | 8 | 320 GB | 7 TB | $80 | Production web/api. |
| `2xlarge_3_0` | 32 GB | 16 | 640 GB | 8 TB | $160 | Heavy production. |

**App+OS minimums (typical):** WordPress / LAMP / Node.js / Django /
Rails / Ghost / Joomla / Magento: `medium_3_0` (4 GB). GitLab / Plesk /
cPanel: `large_3_0` (8 GB).

**App+OS minimums (typical):**
- WordPress / WordPress Multisite: `medium_3_0` (4 GB RAM, 2 CPU).
- LAMP / Node.js / Django / Rails: `medium_3_0` (4 GB RAM, 2 CPU).
- Ghost / Joomla / Magento: `medium_3_0` (4 GB RAM, 2 CPU).
- GitLab / Plesk / cPanel: `large_3_0` (8 GB RAM, 4 CPU).

### Step 3: Availability Zone

```bash
aws lightsail get-regions --include-availability-zones --region us-east-1
```

Lightsail supports a subset of EC2 AZs per region. Use a multi-AZ
deployment for HA: two instances in different AZs behind a Lightsail
load balancer. For databases, choose primary and standby in different
AZs (`master_user_password`, `availability_zone`, `secondary_availability_zone`).

### Step 4: Static IP attachment

```bash
aws lightsail allocate-static-ip --static-ip-name prod-static-ip --region us-east-1
aws lightsail attach-static-ip --static-ip-name prod-static-ip --instance-name prod-instance
```

ALWAYS attach the static IP before configuring DNS A records. The
attachment is free; the static IP is billed only when detached.
Attach to one instance only; a static IP cannot be shared across
instances (use a load balancer for shared entry points).

### Step 5: DNS zone and records

```bash
aws lightsail create-dnszone --domain-name example.com --region us-east-1
aws lightsail create-domain-entry --domain-name example.com \
  --domain-entry '{"name":"app","type":"A","target":"<static-ip>"}'
```

The Lightsail DNS zone is a managed Route 53 hosted zone. To use it,
delegate the domain by setting the Lightsail nameservers at the
registrar. Lightsail DNS supports A, AAAA, CNAME, MX, TXT, NS, SOA,
and PTR records.

### Step 6: VPC peering to the default EC2-VPC

```bash
aws lightsail is-vpc-peered --region us-east-1
aws lightsail peer-vpc --region us-east-1
```

The peering connects the Lightsail VPC to the default EC2-VPC in the
region. After peering, the Lightsail instance can reach RDS, ElastiCache,
private EC2 instances, and VPC endpoints in the default VPC by private
IP. The peering is one-way (Lightsail initiates connections to EC2-VPC;
EC2-VPC cannot initiate to Lightsail).

**For the RDS security group:** allow inbound from the Lightsail VPC
CIDR (typically `172.26.0.0/16`, but verify via
`aws ec2 describe-vpc-peering-connections`). The RDS instance must be
in the default EC2-VPC for the peering to work — RDS in a non-default
VPC requires a transit gateway or VPC peering between the Lightsail
VPC and the non-default VPC.

### Step 7: Snapshots — automatic and manual

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

### Step 8: Lightsail load balancer (Layer 4 TCP/TLS)

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

### Step 9: Container services (optional)

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

### Step 10: Lightsail distribution (CDN, optional)

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

### Step 11: Lightsail database (optional, multi-AZ for HA)

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

### Step 12: Firewall (per-port, per-source)

```bash
aws lightsail put-instance-public-ports --instance-name prod-instance \
  --port-infos '[
    {"fromPort":22,"toPort":22,"protocol":"TCP","cidrs":["10.0.0.0/8"]},
    {"fromPort":80,"toPort":80,"protocol":"TCP","cidrs":["0.0.0.0/0"]},
    {"fromPort":443,"toPort":443,"protocol":"TCP","cidrs":["0.0.0.0/0"]}
  ]'
```

Default firewall: 22, 80, 443 from anywhere. Tighten 22 (SSH) to the
corporate CIDR for production. The firewall is stateful — outbound
response traffic is allowed regardless of inbound rules.

### Step 13: User data (cloud-init)

```bash
aws lightsail create-instances --instance-names prod-instance \
  --availability-zone us-east-1a --bundle-id medium_3_0 \
  --blueprint-id ubuntu_22_04 \
  --user-data '#!/bin/bash
apt-get update
apt-get install -y nginx
systemctl enable nginx
systemctl start nginx'
```

User data is a cloud-init script that runs at first boot as root.
Max 16 KB. Use for package installs, service enablement, and bootstrap
configuration. For app+OS blueprints, user data runs AFTER the bundled
stack starts — use it to override defaults.

### Step 14: SSH key (default or custom)

```bash
aws lightsail download-default-key-pair --region us-east-1 > lightsail-default-key.pem
chmod 600 lightsail-default-key.pem
ssh -i lightsail-default-key.pem ubuntu@<static-ip>
```

Lightsail provides a default SSH key per region per account. Download
once per region. For custom keys, upload via the Lightsail console or
`import-key-pair`. SSH as the blueprint's default user (e.g., `ec2-user`
for Amazon Linux, `ubuntu` for Ubuntu, `admin` for Debian).

## Common patterns

- **LAMP app with static IP + DNS.** OS-only or LAMP blueprint,
  `medium_3_0` bundle, static IP attached, Lightsail DNS zone with
  A record to the static IP, daily automatic snapshots, firewall
  80/443 from anywhere, 22 from corporate CIDR. Single-instance.

- **WordPress HA behind Lightsail LB.** Two `medium_3_0` WordPress
  instances in different AZs, Lightsail LB on 443 with TLS, sticky
  sessions. Multi-AZ Lightsail database for HA. Daily snapshots.

- **RDS private access via VPC peering.** Lightsail instance with
  VPC peering enabled; RDS in default EC2-VPC with `publicly-accessible: false`;
  RDS security group allows inbound from the Lightsail VPC CIDR.

- **Container service for stateless API.** Container service, `small`
  power, scale 2, public endpoint with health check. Image from ECR.
  Use for stateless APIs that don't need a full EC2 instance.

## Output format

```text
INSTANCE_SPEC: <name>
VERDICT: READY_TO_DEPLOY | PREREQUISITES_MISSING
ARCHITECTURE:
  Blueprint: <OS-only | app+OS> <blueprint_id>
  Bundle: <bundle_id> (RAM/CPU/SSD/transfer)
  AZ: <az>
  Static IP: <attached | not required>
  DNS: <zone + A record | not configured>
  VPC peering: <enabled | disabled | not required>
  Snapshots: <automatic daily + manual | none>
  Load balancer: <Lightsail LB TLS 443 | none>
  Container service: <power + scale | none>
  Distribution: <CDN | none>
  Database: <single-AZ | multi-AZ | none>
  Firewall: <22 corporate / 80,443 anywhere>
CHECKLIST:
  [x] Blueprint exists in region
  [x] Bundle meets app+OS minimum (if applicable)
  [x] AZ valid in region
  [x] Static IP attached before DNS A record
  [x] DNS zone created, A record to static IP
  [x] VPC peering enabled (if RDS/ElastiCache access required)
  [x] Automatic snapshots scheduled
  [x] Manual snapshot captured (pre-deploy)
  [x] Load balancer health check configured (if HA)
  [x] Database publicly-accessible false (if database deployed)
  [x] Firewall 22 scoped to corporate CIDR
FINDINGS:
  - [INFO] Estimated monthly cost: $20 (bundle) + $20 (database single-AZ) + $0 (static IP attached)
  - [WARN] VPC peering disabled — instance cannot reach RDS in EC2-VPC
DEPLOY_COMMANDS:
  <ordered list of aws lightsail create-* commands>
```

## STRICT output contract

### Required output structure

Every response MUST begin with this block — no preamble, no
conversational opening:

```text
INSTANCE: <instance-name>
VERDICT: READY_TO_DEPLOY | PREREQUISITES_MISSING
TARGET: <instance-name>
PRE_CHECKS:
  - [PASS] <check description>
  - [FAIL] <check description> — <reason>
STEPS:
  1. CONFIRM: About to <operation> instance <name> in account <account> region <region>. This will <consequence>. Estimated monthly cost: <$X>. Proceed? (yes/no)
  2. <exact CLI command — no placeholders>
POST_VERIFY:
  - [PASS] <verification description>
  - [FAIL] <verification description> — <reason>
BLUEPRINT: <OS-only | app+OS> <blueprint_id>
BUNDLE: <bundle_id> (<RAM>/<CPU>/<SSD>/<transfer>)
STATIC_IP: <attached-name | none>
DNS: <zone + A record | none>
VPC_PEERING: <enabled | disabled | not required>
SNAPSHOTS: <automatic daily N-day retention + manual | none>
NOTES: <HA posture, network reachability, cost breakdown>
```

### FORBIDDEN output patterns

- NEVER start with "Let me analyze…" or "I'll create…" — the VERDICT
  block is the FIRST line, always. No conversational preamble.
- NEVER use lowercase verdict values — emit `READY_TO_DEPLOY` or
  `PREREQUISITES_MISSING` (not `ready`, `prerequisites`).
- NEVER omit PRE_CHECKS — every pre-check run must appear with `[PASS]`
  or `[FAIL]` and a specific reason for each failure.
- NEVER emit a plan with placeholder values (e.g., `<instance-name>`)
  in a READY_TO_DEPLOY plan — every field must be populated with actual
  values from the input.
- NEVER omit the CONFIRM gate as the first STEPS entry for any
  state-changing operation.
- NEVER claim success without verifying the instance is `running` via
  `get-instance-state` — a partial CLI sequence is non-compliant.
- NEVER silently allow `publicly-accessible: true` on a Lightsail
  database — block it explicitly with a [FAIL] pre-check.
- NEVER allow an app+OS blueprint on a bundle below the vendor minimum
  — block at pre-check with the required bundle ID.

### Perfect example output

```text
INSTANCE: prod-lamp
VERDICT: READY_TO_DEPLOY
TARGET: prod-lamp
PRE_CHECKS:
  - [PASS] Blueprint lamp_8 exists in region us-east-1
  - [PASS] Bundle medium_3_0 (4GB/2CPU/80GB/4TB) meets LAMP minimum
  - [PASS] Availability Zone us-east-1a valid in region
  - [PASS] SSH default key exists for region us-east-1
  - [PASS] Static IP prod-lamp-ip allocated, not attached to another instance
  - [PASS] DNS zone example.com exists
  - [PASS] VPC peering not required (no RDS/ElastiCache access in spec)
  - [PASS] Automatic snapshot addon enabled, 05:00 UTC, 7-day retention
  - [PASS] Firewall 22 scoped to corporate CIDR 10.0.0.0/8
  - [PASS] IAM principal holds lightsail:CreateInstances, AttachStaticIp, EnableAddOn, CreateDomainEntry
STEPS:
  1. CONFIRM: About to create-instances prod-lamp in account 111111111111 region us-east-1. LAMP 8 on medium_3_0 (4GB/2CPU/80GB/4TB), AZ us-east-1a, static IP prod-lamp-ip, DNS A app.example.com, daily snapshots. Cost ~$20/mo. Proceed? (yes/no)
  2. aws lightsail create-instances --instance-names prod-lamp --availability-zone us-east-1a --bundle-id medium_3_0 --blueprint-id lamp_8 --user-data '<custom-php-config>' --region us-east-1
  3. aws lightsail wait-instance-running --instance-name prod-lamp
  4. aws lightsail attach-static-ip --static-ip-name prod-lamp-ip --instance-name prod-lamp --region us-east-1
  5. aws lightsail create-domain-entry --domain-name example.com --domain-entry '{"name":"app","type":"A","target":"<static-ip>"}' --region us-east-1
  6. aws lightsail enable-add-on --resource-name prod-lamp --add-on-request '{"addOnType":"AutoSnapshot","snapshotTimeOfDay":"05:00","status":"Active"}' --region us-east-1
  7. aws lightsail put-instance-public-ports --instance-name prod-lamp --port-infos '[{"fromPort":22,"toPort":22,"protocol":"TCP","cidrs":["10.0.0.0/8"]},{"fromPort":80,"toPort":80,"protocol":"TCP","cidrs":["0.0.0.0/0"]},{"fromPort":443,"toPort":443,"protocol":"TCP","cidrs":["0.0.0.0/0"]}]' --region us-east-1
POST_VERIFY:
  - (pending execution)
  - get-instance-state returns running
  - get-instance returns the static IP as publicIpAddress
  - get-domain returns A app.example.com → <static-ip>
BLUEPRINT: app+OS lamp_8
BUNDLE: medium_3_0 (4 GB / 2 CPU / 80 GB SSD / 4 TB transfer)
STATIC_IP: prod-lamp-ip attached
DNS: example.com A app → <static-ip>
VPC_PEERING: not required
SNAPSHOTS: automatic daily 05:00 UTC, 7-day retention
NOTES:
  - Single-instance — no HA. For HA, deploy a second instance in us-east-1b behind a Lightsail load balancer.
  - Bundle includes 4 TB/month outbound transfer. Overage billed at $0.09/GB.
  - Static IP free while attached; billed $3.60/mo if detached.
  - LAMP admin password generated at launch — capture immediately; not retrievable later.
```

## NEVER (top 5)

These are the highest-impact, most-frequent failure modes in Lightsail
deployments. Violating any one of these is a correctness or security
regression.

1. **NEVER configure DNS A records before attaching a static IP.**
   Without a static IP, the instance's public IP changes on stop/start
   — DNS records silently break. Attach the static IP first, then
   create the A record. Pre-check this ordering.

2. **NEVER assume Lightsail can reach RDS without VPC peering.**
   Lightsail lives in its own VPC, isolated from the default EC2-VPC.
   `peer-vpc` is per-region and MUST be enabled before the instance
   can reach RDS, ElastiCache, or private EC2. Pre-check
   `is-vpc-peered` whenever private resource access is required.

3. **NEVER deploy a production database with `publicly-accessible:
   true`.** It exposes the DB to the internet. Always set
   `publicly-accessible: false`; reach the DB via peered Lightsail
   instances by private IP. Block at pre-check.

4. **NEVER deploy an app+OS blueprint on a bundle below the vendor
   minimum.** WordPress on `nano_3_0` (512 MB RAM) installs but fails
   under load — MySQL OOMs, PHP-FPM exhausts workers. Pre-check the
   bundle against the blueprint minimum (`medium_3_0` for most app+OS).

5. **NEVER leave orphan static IPs.** Attached: free. Detached:
   $0.005/hour (~$3.60/mo). When deleting an instance, also
   `release-static-ip` any IP no longer needed. Pre-check the static
   IP inventory.

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

## AWS documentation

- **Amazon Lightsail Documentation** — https://docs.aws.amazon.com/lightsail/
- **Lightsail instances** — https://docs.aws.amazon.com/lightsail/latest/userguide/amazon-lightsail-compute.html
- **Lightsail blueprints and bundles** — https://docs.aws.amazon.com/lightsail/latest/userguide/amazon-lightsail-choose-blueprint-and-instance.html
- **Lightsail static IPs** — https://docs.aws.amazon.com/lightsail/latest/userguide/lightsail-static-ip-assigning.html
- **Lightsail DNS zones** — https://docs.aws.amazon.com/lightsail/latest/userguide/lightsail-how-to-create-dns-zone.html
- **Lightsail VPC peering** — https://docs.aws.amazon.com/lightsail/latest/userguide/amazon-lightsail-understanding-database-amazon-vpc-peering.html
- **Lightsail snapshots** — https://docs.aws.amazon.com/lightsail/latest/userguide/amazon-lightsail-creating-instance-snapshots.html
- **Lightsail load balancers** — https://docs.aws.amazon.com/lightsail/latest/userguide/lightsail-how-to-create-load-balancer.html
- **Lightsail container services** — https://docs.aws.amazon.com/lightsail/latest/userguide/amazon-lightsail-container-services.html
- **Lightsail distributions** — https://docs.aws.amazon.com/lightsail/latest/userguide/amazon-lightsail-content-delivery-distribution.html
- **Lightsail databases** — https://docs.aws.amazon.com/lightsail/latest/userguide/amazon-lightsail-relational-databases.html
- **Lightsail API Reference** — https://docs.aws.amazon.com/lightsail/2016-11-28/api-reference/
