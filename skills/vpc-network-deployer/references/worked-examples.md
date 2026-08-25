# Worked Examples — VPC Network Deployer

Deep reference content moved verbatim from `vpc-network-deployer/SKILL.md`. Loaded on demand;
see SKILL.md for the condensed core and its quick navigation.

## PREREQUISITES_MISSING output example (incomplete deployment spec)

```text
VPC_SPEC: <name-or-unknown>
VERDICT: PREREQUISITES_MISSING
REASON: Deployment specification is missing required fields (<list>).
Cannot produce a deployment plan without <field> — the resulting VPC
would be non-functional or insecure.
REQUIRED:
  - region (AWS region for the VPC)
  - cidr_block (RFC 1918 range, /16 minimum for production)
  - az_count (2 minimum, 3 recommended)
  - nat_strategy (HA or cost-optimized)
  - tier_list (public, private, database — at least private required)
```
