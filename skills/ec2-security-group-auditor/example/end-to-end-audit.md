# Example: End-to-End Security Group Audit

A walkthrough showing how the `ec2-security-group-auditor` skill processes a
realistic multi-rule security group, from input through verdict to remediation.

---

## Scenario

A platform team is preparing to deploy a three-tier web application into a new
VPC. They have created four security groups and want to validate them before
production launch. The security lead asks: "Audit these security groups for
public exposure and compliance violations."

## Input

The team provides the following security group configurations:

### SG 1: app-alb-sg (Application Load Balancer)

```
Security Group: app-alb-sg
Inbound rules:
  - Port: 443
    Protocol: TCP
    Source: 0.0.0.0/0
  - Port: 80
    Protocol: TCP
    Source: 0.0.0.0/0
```

### SG 2: app-tier-sg (Application Tier)

```
Security Group: app-tier-sg
Inbound rules:
  - Port: 443
    Protocol: TCP
    Source: sg-alb-0abc123def
```

### SG 3: db-tier-sg (Database Tier)

```
Security Group: db-tier-sg
Inbound rules:
  - Port: 3306
    Protocol: TCP
    Source: 0.0.0.0/0
  - Port: 22
    Protocol: TCP
    Source: 0.0.0.0/0
```

### SG 4: admin-sg (Emergency Access)

```
Security Group: admin-sg
Inbound rules:
  - Port: 0-65535
    Protocol: TCP
    Source: 0.0.0.0/0
```

## Skill Output

### SG 1: app-alb-sg

```
SECURITY_GROUP: app-alb-sg
VERDICT: PUBLIC_NONCRITICAL
SEVERITY: Low
CIS_CONTROLS: N/A
REASON: Port 443 TCP from 0.0.0.0/0 is a non-critical port from a public
source (PUBLIC_NONCRITICAL). Port 80 TCP from 0.0.0.0/0 is also
PUBLIC_NONCRITICAL. Aggregate: PUBLIC_NONCRITICAL. Both ports are standard
for an internet-facing ALB.
REMEDIATION: Verify the ALB forwards to backend instances via SG reference
(sg-app-tier), not direct 0.0.0.0/0 on the backend. Ensure HTTP (80)
redirects to HTTPS (443). No action required if behind ALB.
```

### SG 2: app-tier-sg

```
SECURITY_GROUP: app-tier-sg
VERDICT: RESTRICTED
SEVERITY: None
CIS_CONTROLS: N/A
REASON: Port 443 TCP from sg-alb-0abc123def is a security group reference
(RESTRICTED source). Aggregate: RESTRICTED. No public exposure.
REMEDIATION: None required.
```

### SG 3: db-tier-sg

```
SECURITY_GROUP: db-tier-sg
VERDICT: OPEN
SEVERITY: Critical
CIS_CONTROLS: 5.1, 5.3
REASON: Port 3306 TCP from 0.0.0.0/0 — MySQL exposed to the internet is a
critical data-exfiltration risk (OPEN). Port 22 TCP from 0.0.0.0/0 — SSH
open to the internet is a CIS 5.1 violation (OPEN). Aggregate: OPEN.
REMEDIATION: P0 — restrict port 3306 to the application-tier SG ID
(sg-app-tier) ONLY. Database subnets must have no IGW route. Remove SSH
(22) from 0.0.0.0/0 entirely; use SSM Session Manager for access. This is
a direct CIS 5.1 and PCI-DSS 1.3.1 violation.
```

### SG 4: admin-sg

```
SECURITY_GROUP: admin-sg
VERDICT: OPEN
SEVERITY: Critical
CIS_CONTROLS: 5.3
REASON: Port 0-65535 TCP from 0.0.0.0/0 — all TCP ports open to the
internet. The range intersects every high-risk port in the registry (22,
3306, 3389, 5432, 6379, etc.). This is maximum exposure. Aggregate: OPEN.
REMEDIATION: P0 — delete this rule entirely. Recreate with ONLY the specific
ports the workload requires. An all-ports rule from 0.0.0.0/0 is the AWS
equivalent of disabling the firewall.
```

## Orchestrator Integration

After the audit, the orchestrator would emit:

```
[Phase: Audit | Skills routed: ec2-security-group-auditor]
  app-alb-sg:    PUBLIC_NONCRITICAL (Low)
  app-tier-sg:   RESTRICTED (None)
  db-tier-sg:    OPEN (Critical) — CIS 5.1 violation
  admin-sg:      OPEN (Critical) — maximum exposure

[Phase: Prioritize | Findings: 2 CRITICAL | Skills routed: aws-orchestrator]
  1. CRITICAL: admin-sg — all ports to internet (P0, fix immediately)
  2. CRITICAL: db-tier-sg — MySQL + SSH to internet (P0, CIS 5.1)
  3. Low: app-alb-sg — verify ALB backend SG ref

[Phase: Remediate | Skills routed: ec2-security-group-auditor]
  - admin-sg: delete 0-65535 rule, recreate with specific ports
  - db-tier-sg: restrict 3306 to sg-app-tier, remove SSH, use Session Manager
  - app-alb-sg: verify backend uses SG ref (no action if correct)
```

## Key Takeaways

1. **Source classification first.** The skill evaluates the source (CIDR, SG-ref,
   prefix list) before the port. Port 22 from `10.0.0.0/8` is RESTRICTED; the
   same port from `0.0.0.0/0` is OPEN.
2. **Worst-case aggregation.** A single OPEN rule makes the entire SG OPEN,
   regardless of how restrictive the other rules are.
3. **Port range intersection.** The `0-65535` range intersects all high-risk
   ports, so it is always classified as CRITICAL — never treated as a single
   non-critical port.
4. **Compliance mapping.** Each OPEN finding cites the specific CIS, PCI-DSS,
   and NIST control IDs for audit traceability.
