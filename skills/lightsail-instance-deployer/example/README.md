# End-to-end usage scenario: lightsail-instance-deployer

A walkthrough showing the skill producing a deployment plan for a
production LAMP blueprint Lightsail instance with a static IP, DNS A
record, daily automatic snapshots, and a tightened firewall.
Demonstrates the READY_TO_DEPLOY verdict, architecture checklist,
and ordered deploy-command list.

## Input (user prompt)

> Provision a Lightsail instance for our marketing site. Use the LAMP
> blueprint, a medium bundle, in us-east-1a. We have a static IP
> `prod-lamp-ip` already allocated. We need DNS `app.example.com`
> pointing at the instance, daily snapshots at 05:00 UTC, and the
> firewall tightened: SSH only from our corporate CIDR 10.0.0.0/8,
> HTTP/HTTPS from anywhere. No RDS access needed.

## Expected behavior

1. **Pre-flight:** The skill validates the spec — blueprint (`lamp_8`)
   exists in us-east-1, bundle (`medium_3_0`) meets LAMP minimum,
   AZ valid, SSH key exists, static IP allocated, DNS zone exists, IAM
   permissions confirmed. VPC peering not required.
2. **Bundle check:** Verifies `medium_3_0` (4 GB RAM) meets the LAMP
   app+OS minimum. PASS.
3. **Static IP ordering:** Verifies the static IP is allocated and not
   attached to another instance. The plan attaches the IP BEFORE
   creating the DNS A record (avoids IP churn).
4. **Snapshots:** Plans the AutoSnapshot addon at 05:00 UTC with
   7-day default retention.
5. **Firewall:** Plans 22 from `10.0.0.0/8` (corporate), 80/443 from
   `0.0.0.0/0`.
6. **Verdict:** READY_TO_DEPLOY — all checklist dimensions pass.

## Expected output

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

## What the baseline (no-skill) response misses

A generic assistant without this skill would:
- Not enumerate the 10 pre-check dimensions (blueprint in region,
  bundle meets app+OS minimum, AZ valid, SSH key exists, static IP
  ordering, DNS zone, IAM permissions, VPC peering for RDS, snapshot
  addon, firewall CIDR scoping).
- Not surface the static-IP-before-DNS-A-record ordering rule (the
  #1 cause of broken DNS after Lightsail stop/start).
- Not flag the bundle-minimum requirement for app+OS blueprints.
- Not include the CONFIRM gate with cost estimate.
- Not produce a deterministic VERDICT block for downstream
  automation.

The skill converts an open-ended "set up LAMP on Lightsail" prompt
into a deterministic, pre-checked, ordered deploy plan with a single
READY_TO_DEPLOY or PREREQUISITES_MISSING verdict.
