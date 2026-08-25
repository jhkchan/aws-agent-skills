# Error Handling — Client VPN Endpoint Deployer

Load-on-demand error handling moved verbatim from SKILL.md.

## Error handling — symptom mappings

### Clients connect but cannot reach any IP
- Missing authorization rule. Create at least one
  `authorize-client-vpn-ingress` rule. Without it, clients route nowhere.

### DNS resolution fails for VPC hostnames in split-tunnel
- Custom DNS servers not configured. Set `DnsServers=["<VPC-DNS>"]`.

### Subnet association fails with association limit exceeded
- AWS processes associations sequentially. Wait for existing
  associations to reach `available` before creating new ones.

### Authorization rule shadows specific rule
- Rules are first-match-wins. Delete and recreate in the correct order
  (specific first, broad last).
