# EC2 Security-Group Auditor — advanced patterns (moved from SKILL.md)

Loaded on demand — content moved verbatim from SKILL.md (progressive disclosure; nothing deleted).
## AWS dataplane expert details (Mindset — non-obvious AWS behavior) (moved from SKILL.md)

These AWS-specific behaviors are NOT in the port registry but routinely
trip up audits. Internalize them before emitting any verdict.

### Rule evaluation is UNION, not first-match

AWS security groups do NOT use first-match priority. Every inbound allow
rule is independently evaluated against the packet; the **union** of all
allow rules is the effective permission. There is no "deny" rule in SGs
— denies live in Network ACLs, which ARE stateless and ordered. Practical
consequence: adding a tighter rule on the same port+source does NOT
override an existing `0.0.0.0/0` rule — you must REMOVE the broader
rule. This is precisely why the procedure aggregates to the WORST
per-rule verdict, not the "best" or "most specific."

### Stateful conntrack has a per-ENI ceiling

Return traffic for an allowed outbound flow is auto-permitted via
connection tracking. Each ENI's conntrack table is sized by instance
type (see EC2 network performance specs — r5n.16xlarge ~600k entries,
t3.micro far less). Under sustained high packets-per-second the table
can exhaust, at which point AWS falls back to strict-flow pinning and
some established flows may drop. This is NOT a reason to add inbound
ephemeral rules — the SG is still stateful. It IS a reason to monitor
`conntrack_allowance_exceeded` in CloudWatch `etwpm`.

### Source field has four distinct shapes in the API

`DescribeSecurityGroups` returns sources in four separate arrays:
`IpRanges` (IPv4), `Ipv6Ranges` (IPv6), `UserIdGroupPairs` (SG refs),
`PrefixListIds` (managed prefix lists). A naive auditor that only
checks `IpRanges` will miss IPv6 exposure, SG-ref cycles, and
prefix-list drift. Iterate ALL FOUR arrays every time. The
classification table treats them uniformly; the API does not.

### Quotas that change the audit posture

- `sg-rules-per-sg` quota: default 60 inbound + 60 outbound rules per
  SG (raisable). An SG near the limit is itself a smell — rule sprawl
  obscures the real posture and slows dataplane propagation.
- `SGs-per-ENI` quota: default 5. Effective permission across 5 SGs
  is the union of up to 300 inbound rules per interface.
- The VPC default SG **cannot be deleted** — only its rules can. CIS
  5.4 specifically targets leaving it open. Always include the default
  SG in scope even when "unused"; AWS re-attaches it to new ENIs in
  some launch paths.

### VPC peering, RAM sharing, and cross-VPC SG references

- SG IDs are **region-scoped** and CANNOT be referenced from another
  VPC, even over a peering connection. Cross-VPC rules must use CIDRs
  — which means there is no SG-ref guardrail on the peer side.
- Over peering, the peer VPC's effective posture depends on rules YOU
  cannot see. Flag any peered-CIDR source as "external-trust" and
  require periodic re-validation.
- In AWS RAM shared subnets, participant accounts can create SGs in
  the shared VPC. The owner account's audit MUST enumerate SGs across
  all participants (`--owner self` filter excludes them — drop it).

### Prefix-list versioning and drift

Every modification to a managed prefix list bumps `Version`. Use
`--version <current>` for optimistic locking. For periodic re-audit,
store the version observed at last review and compare; if `Version`
advanced without a corresponding change ticket, the list has drifted.
AWS-managed lists (e.g., CloudFront `pl-xxxxxxxx` for global edge IPs)
rotate entries as POPs are added — treat their classification as
"valid as of timestamp T", not timeless.

### AWS Config + Security Hub control IDs

Map findings to the downstream tooling auditors actually run — they
will find the finding in Security Hub before they read your report:

| Finding | AWS Config managed rule | Security Hub control |
| --- | --- | --- |
| SSH (22) from `0.0.0.0/0` | `restricted-common-ports` | **EC2.2** |
| RDP (3389) from `0.0.0.0/0` | `restricted-common-ports` | **EC2.18** |
| SG not attached to any ENI | `ec2-security-group-attached-to-eni` | EC2.4 |
| Default SG allows any traffic | — | **EC2.19** (CIS 5.4) |
| Any other port from `0.0.0.0/0` | `vpc-sg-open-only-to-authorized-ports` | — |
| Public launch + open SG combined | — | **EC2.15** |

Cite BOTH the CIS control AND the Security Hub control ID in the
REMEDIATION field — the remediation owner usually triages via
Security Hub.

### Reachability Analyzer confirms the actual path

For borderline cases ("is the SG reachable through a TGW or peering
route?"), use VPC Reachability Analyzer — it evaluates SG + route
table + peering together, while the SG rule alone does not guarantee
a reachable path:

```
aws ec2 create-network-insights-path \
  --source <source-eni> --destination <ip> \
  --protocol tcp --destination-port <port>
aws ec2 start-network-insights-analysis \
  --network-insights-path-id <path-id>
```

Use it to CONFIRM OPEN verdicts that depend on a specific ingress
path, and to REFUTE RESTRICTED claims when a transit gateway makes
the SG effectively reachable from an unexpected CIDR.

## Recent AWS features (2024-2026) (moved from SKILL.md)

- **Security group VPC associations (2024):** Security groups can now be associated with specific VPCs, and VPC-scoped security groups can be shared across accounts via RAM. Auditors should verify that cross-account shared security groups do not inadvertently grant inbound exposure to unexpected principals.
- **VPC Lattice security policy integration (2024-2025):** VPC Lattice uses its own authorization model but interacts with security groups. Auditors should note that Lattice-managed traffic may not appear in standard security group rule evaluation — verify that Lattice target groups have appropriate authorization policies.
- **Prefix list improvements (2024):** Managed prefix lists now support more entries and customer-managed prefix lists can be shared across accounts. Auditors should verify that shared prefix lists are governed — a compromised prefix list can silently widen security group ingress.
