# Worked examples — lightsail-instance-deployer

Example templates and pattern catalogs moved verbatim from SKILL.md for progressive disclosure. Load on demand.

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
