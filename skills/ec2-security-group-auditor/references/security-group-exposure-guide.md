# EC2 Security Group Exposure Reference Guide

Supplementary reference for the EC2 Security-Group Auditor skill.

## High-risk port registry

Ports classified as critical when exposed to `0.0.0.0/0`:

| Port(s) | Protocol | Service | Risk |
| --- | --- | --- | --- |
| 22 | TCP | SSH | Brute-force target #1 — botnets scan within minutes |
| 3389 | TCP | RDP | Brute-force / exploit target |
| 3306 | TCP | MySQL | Database exposure — data breach vector |
| 5432 | TCP | PostgreSQL | Database exposure — data breach vector |
| 1433 | TCP | MSSQL | Database exposure — data breach vector |
| 27017 | TCP | MongoDB | NoSQL exposure — ransomware vector |
| 6379 | TCP | Redis | In-memory DB exposure — cryptomining + data exfil |
| 9200 | TCP | Elasticsearch | Search engine exposure — data exfil + ransomware |
| 0-65535 | TCP | All ports | Maximum exposure — every service is attackable |

## CIDR classification

| Source | Classification | Notes |
| --- | --- | --- |
| `0.0.0.0/0` | Internet (all IPv4) | Publicly reachable from anywhere |
| `::/0` | Internet (all IPv6) | Publicly reachable from anywhere |
| `10.0.0.0/8` | Private (RFC 1918) | Internal traffic only |
| `172.16.0.0/12` | Private (RFC 1918) | Internal traffic only |
| `192.168.0.0/16` | Private (RFC 1918) | Internal traffic only |
| `sg-xxxxxxxx` | Security group ref | Restricted to instances in that SG |
| Specific IP (e.g., `203.0.113.5/32`) | Known IP | Restricted to a single source |

## Classification decision tree

```
Any rule has Source: 0.0.0.0/0 (or ::/0) on a high-risk port?
  -> OPEN (critical exposure)

Any rule has Source: 0.0.0.0/0 on a non-critical port (e.g., 80, 443)?
  -> PUBLIC_NONCRITICAL (public, but low-risk service)

All rules restricted to private CIDR / SG ref / specific IP?
  -> RESTRICTED

No inbound rules?
  -> RESTRICTED (locked down)
```

## Remediation patterns

### SSH (port 22)
- **Preferred:** Remove inbound SSH rule entirely. Use AWS Systems Manager
  Session Manager for shell access — no open ports, IAM-authenticated,
  fully audited.
- **Fallback:** Restrict to a bastion host security group ID
  (`sg-xxxxxxxx`) rather than a CIDR.

### Databases (3306, 5432, 1433, 27017, 6379, 9200)
- Restrict the source to the application-tier security group ID only.
- Database subnets should have no internet gateway route (private subnet).

### All-ports rules (0-65535)
- Delete entirely. Recreate with only the specific ports the workload
  requires. An all-ports rule from `0.0.0.0/0` is the AWS equivalent of
  disabling the firewall.

### Web tiers (80, 443)
- Public HTTPS/HTTP is acceptable for web-facing tiers behind a load
  balancer or WAF. Verify the listener points to an ALB/NLB, not directly
  to an instance.
