# Eval prompt: lamp-app-static-ip-dns-ready

Design a deployment plan for a production Lightsail instance. Emit
the standard VERDICT block (INSTANCE_SPEC, VERDICT, ARCHITECTURE,
CHECKLIST, FINDINGS, DEPLOY_COMMANDS).

Requirements:

- Instance name: prod-lamp
- Blueprint: LAMP 8 (app+OS, blueprint_id lamp_8)
- Bundle: medium_3_0 (4 GB RAM, 2 CPU, 80 GB SSD, 4 TB transfer) —
  meets the LAMP stack minimum
- Availability Zone: us-east-1a (valid in region)
- Static IP: prod-lamp-ip (allocated, not attached to another instance)
- DNS: zone example.com exists; A record app.example.com → static IP
- Snapshots: automatic daily at 05:00 UTC, 7-day retention
- Firewall: 22 from corporate CIDR 10.0.0.0/8; 80 and 443 from
  0.0.0.0/0
- VPC peering: not required (no RDS/ElastiCache access)

Existing-account context: two existing LAMP instances on medium_3_0
have been running for months without issue. The static IP prod-lamp-ip
was allocated yesterday and is not attached to any instance. The
DNS zone example.com exists with two existing A records. IAM principal
holds lightsail:CreateInstances, AttachStaticIp, EnableAddOn,
CreateDomainEntry, PutInstancePublicPorts.
