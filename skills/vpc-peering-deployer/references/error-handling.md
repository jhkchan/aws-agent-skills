# Error Handling — VPC Peering Deployer

Deep reference content moved verbatim from `vpc-peering-deployer/SKILL.md`. Loaded on demand;
see SKILL.md for the condensed core and its quick navigation.

## Error handling deep dives

### Peering stuck in pending-acceptance
- The accepter has not accepted. For same-account, accept manually. For
  cross-account, ensure the accepter account has IAM permission and
  runs `accept-vpc-peering-connection` (or automate via role assumption).

### Traffic not flowing despite ACTIVE peering
- Missing route table entry. Verify BOTH sides have routes to the
  peered VPC's CIDR via the peering connection ID. This is the #1
  cause. Check with `describe-route-tables`.

### DNS resolution not working across peered VPCs
- `AllowDnsResolutionFromPeeredVpc` not enabled on BOTH sides. Verify
  both VPCs have `enableDnsHostnames` and `enableDnsSupport` true. Then
  enable the peering DNS flag on both requester and accepter.

### Security group cross-reference fails
- Cross-account or inter-region peering does NOT support SG cross-
  references. Switch to CIDR-based SG rules for these topologies.

### CIDR overlap detected
- The VPCs have overlapping CIDR blocks. The peering may have been
  created but routing is ambiguous. Re-design CIDR allocation with
  non-overlapping ranges, or use NAT/TGW if overlap is unavoidable.
