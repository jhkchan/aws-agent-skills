---
description: Provision a production-grade Amazon Lightsail instance with blueprint, bundle, static IP, DNS, VPC peering, snapshots, and optional load balancer, container service, distribution, or multi-AZ database.
nl_triggers:
  - "create a Lightsail instance"
  - "provision a Lightsail instance with static IP"
  - "Lightsail blueprint selection"
  - "Lightsail bundle plan sizing"
  - "Lightsail DNS zone"
  - "Lightsail VPC peering to EC2-VPC"
  - "Lightsail RDS private access"
  - "Lightsail automatic snapshots"
  - "Lightsail load balancer"
  - "Lightsail container service"
  - "Lightsail distribution CDN"
  - "Lightsail multi-AZ database"
  - "WordPress on Lightsail"
  - "LAMP on Lightsail"
routes_to: lightsail-instance-deployer
---

# /aws:deploy-lightsail-instance

Activate the `lightsail-instance-deployer` skill and produce a
deployment plan for a production-grade Amazon Lightsail instance with
secure defaults.

## What it does

Reads a deployment specification (blueprint, bundle, AZ, static IP,
DNS, VPC peering, snapshots, load balancer, container service,
distribution, database) and produces an ordered deployment plan with:

1. Pre-flight specification gate — validates blueprint exists in
   region, bundle meets app+OS minimum (if applicable), AZ valid,
   SSH key exists, static IP allocated, DNS zone exists, VPC peering
   enabled if RDS/ElastiCache access required, IAM permissions
   confirmed. Blocks deployment (PREREQUISITES_MISSING) on missing
   fields or invalid config.
2. Blueprint selection — OS-only (Amazon Linux 2023, Ubuntu, Debian)
   for custom stacks, or app+OS (WordPress, LAMP, Node.js, Django,
   Rails, Ghost, Joomla, Magento) for bundled stacks with vendor
   defaults.
3. Bundle (plan) sizing — RAM/CPU/SSD/transfer fits the workload.
   App+OS blueprints require a minimum bundle (typically `medium_3_0`,
   4 GB RAM). Validates vendor minimum is met.
4. Availability Zone — valid AZ in the selected region (Lightsail may
   not support all EC2 AZs).
5. Static IP attachment — attaches BEFORE creating the DNS A record
   (avoids IP churn on stop/start). Static IP is free while attached;
   billed $0.005/hour when detached.
6. DNS zone and records — Lightsail DNS zone (managed Route 53) with
   A record pointing to the static IP.
7. VPC peering to the default EC2-VPC — enables private access to
   RDS, ElastiCache, and private EC2 instances. One-way (Lightsail →
   EC2-VPC), per-region.
8. Snapshots — automatic (daily schedule, 7-day default retention) +
   manual (pre-deploy/pre-update baseline).
9. Load balancer (optional) — Lightsail LB (Layer 4 TCP/TLS) with
   health checks and sticky sessions for HA.
10. Container service (optional) — managed ECS-like platform for
    containerized apps.
11. Distribution (optional) — Lightsail distribution (CloudFront-backed
    CDN) fronting an instance or bucket.
12. Database (optional) — multi-AZ managed Lightsail database for HA.
13. Firewall — per-port, per-source rules (default 22, 80, 443;
    tighten 22 to corporate CIDR for production).
14. User data (optional) — cloud-init launch script (max 16 KB).

Emits a deterministic deployment plan per instance:

```text
INSTANCE: <name>
VERDICT: READY_TO_DEPLOY | PREREQUISITES_MISSING
TARGET: <name>
PRE_CHECKS:
  - [PASS] <check description>
  - [FAIL] <check description> — <reason>
STEPS:
  1. CONFIRM: About to <operation> instance <name> in account <account> region <region>. Estimated monthly cost: <$X>. Proceed? (yes/no)
  2. <exact CLI command — no placeholders>
POST_VERIFY:
  - [PASS] <verification description>
BLUEPRINT: <OS-only | app+OS> <blueprint_id>
BUNDLE: <bundle_id> (<RAM>/<CPU>/<SSD>/<transfer>)
STATIC_IP: <attached-name | none>
DNS: <zone + A record | none>
VPC_PEERING: <enabled | disabled | not required>
SNAPSHOTS: <automatic daily N-day retention + manual | none>
NOTES: <HA posture, network reachability, cost breakdown>
```

## When to invoke

Provide a deployment spec and ask any of:

- "provision a Lightsail instance with a static IP"
- "WordPress on Lightsail with daily snapshots"
- "LAMP instance with DNS A record"
- "Lightsail instance that can reach my RDS"
- "Lightsail container service for my API"
- "Lightsail distribution in front of my static site"
- "multi-AZ Lightsail database for HA"

A bare blueprint + bundle + "deploy Lightsail" also routes here via
the orchestrator.

## Inputs

- **Required:** blueprint_id (OS-only or app+OS), bundle_id (plan),
  availability_zone.
- **Optional:** static_ip_name (allocate or attach existing),
  dns_zone_name + dns_record (A record to static IP),
  vpc_peering_required (true/false), snapshot_schedule (none/daily),
  load_balancer_config, container_service_config, distribution_config,
  database_config, firewall_rules, user_data, ssh_key_name.

## Outputs

- One VERDICT block per instance (READY_TO_DEPLOY or
  PREREQUISITES_MISSING).
- PRE_CHECKS with all dimensions validated (blueprint, bundle,
  AZ, SSH key, static IP, DNS zone, VPC peering, snapshots, IAM).
- STEPS with ordered `aws lightsail create-*` and `attach-*`
  commands, starting with the CONFIRM gate.
- POST_VERIFY with verification steps (get-instance-state returns
  running, static IP attached as publicIpAddress, A record resolves).
- NOTES with HA posture, network reachability, and cost breakdown.

## Related

- `/aws:pipeline` to enter the full CloudOps pipeline (this skill is
  the Phase 1 Deploy specialist for Lightsail compute).
- `/aws:audit-rds-instance` for RDS security auditing when Lightsail
  reaches RDS via VPC peering.
- `/aws:deploy-cloudfront-distribution` for full CloudFront when the
  Lightsail distribution is too limited (multi-origin, WAF,
  Lambda@Edge).
