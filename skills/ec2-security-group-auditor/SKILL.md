---
name: ec2-security-group-auditor
description: >-
  Audits EC2 security group rules to identify publicly exposed ports and
  provides remediation guidance. Use when reviewing security groups, checking
  for open SSH/RDP/database ports, validating network exposure, or tightening
  inbound firewall rules.
version: 0.1.0
---

# EC2 Security-Group Auditor

An AWS CloudOps agent skill that analyzes EC2 security group inbound rules
to identify publicly exposed ports, classify each security group's exposure
level, and provide specific remediation guidance.

## Classification logic (apply in order)

1. If any inbound rule has `Source: 0.0.0.0/0` (or `::/0` for IPv6) on any
   port in the high-risk set (22 SSH, 3389 RDP, 3306 MySQL, 5432 PostgreSQL,
   1433 MSSQL, 27017 MongoDB, 6379 Redis, 9200 Elasticsearch, or
   `0-65535` all ports), the security group is **OPEN** (publicly exposed
   critical service — direct attack surface on the internet).

2. If any inbound rule has `Source: 0.0.0.0/0` on a port outside the
   high-risk set (e.g., 80 HTTP, 443 HTTPS), the security group is
   **PUBLIC_NONCRITICAL** (publicly accessible on non-critical ports —
   acceptable for web-facing tiers but should be reviewed for necessity).

3. If all inbound rules have `Source` restricted to private CIDR ranges
   (e.g., `10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`, a specific
   security group ID `sg-xxxxxxxx`, or a specific IP), the security group
   is **RESTRICTED** (private access only — no direct internet exposure).

4. If a security group has no inbound rules, it is **RESTRICTED** (no
   inbound access — fully locked down).

## Output format (per security group)

```text
SECURITY_GROUP: <name>
VERDICT: OPEN | PUBLIC_NONCRITICAL | RESTRICTED
REASON: <1-2 sentences citing the specific rules>
REMEDIATION: <specific action, or "None required" if restricted>
```

## NEVER

- NEVER classify SSH (port 22) or RDP (port 3389) open to `0.0.0.0/0` as
  anything other than **OPEN**. These are the most brute-forced ports on
  the internet — botnets scan them within minutes of launch.

- NEVER classify `0-65535` from `0.0.0.0/0` as merely RESTRICTED. All TCP
  ports to the internet is maximum exposure — every service running on the
  instance is directly attackable.

- NEVER assume a port is safe because the service is "just a database."
  MySQL (3306), PostgreSQL (5432), and Redis (6379) exposed to the internet
  are the root cause of countless data breaches.

- NEVER recommend simply deleting a rule without providing the replacement
  (e.g., a bastion SG reference or SSM Session Manager for SSH access).

## Remediation guidance

For **OPEN** security groups:

- Replace `0.0.0.0/0` on critical ports with a private CIDR, a specific
  security group ID, or a known IP range.
- For SSH (22): use AWS Systems Manager Session Manager instead of direct
  SSH, or restrict to a bastion host security group.
- For databases (3306, 5432, 1433): restrict to the application-tier
  security group ID only.
- For all-ports rules: delete and recreate with only the ports the workload
  requires.

For **PUBLIC_NONCRITICAL** security groups:

- Public HTTPS (443) is acceptable for web-facing tiers; verify it is
  behind a load balancer or WAF.
- Review whether the public exposure is necessary.

For **RESTRICTED** security groups:

- No remediation required for private-CIDR rules.

## Domain

AWS CloudOps / EC2 Network Security & Compliance.
