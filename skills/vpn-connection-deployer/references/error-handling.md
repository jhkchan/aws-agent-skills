# Error Handling - vpn-connection-deployer

## VPN failure deep dives (moved from SKILL.md 'Error handling')

### Tunnels stuck DOWN
- The customer device has not loaded the configuration or has not
  initiated. Verify the configuration XML loaded (from
  `describe-vpn-connections --query CustomerGatewayConfiguration`).
  Check IPSec parameters (IKE, encryption, PSK) match on both sides.
  For NAT'd devices, verify UDP NAT-T is enabled and the NAT allows
  UDP 500/4500.

### Tunnels UP but no traffic flows
- Routes are missing on one side. Static: verify
  `create-vpn-connection-route` was called per prefix. BGP: verify the
  BGP session is established. VPG-attached: verify
  `enable-vgw-route-propagation`. TGW-attached: verify the attachment
  is associated with a TGW route table with propagation enabled.

### Tunnels come UP but drop after ~1 hour
- Phase 2 SA lifetime or parameter mismatch. Phase 2 rekey happens at
  the lifetime boundary (~3600s). If Phase 2 parameters do not match,
  the tunnel drops at the first rekey. Verify Phase 2 parameters.

### BGP session never establishes
- BGP ASN mismatch, or BGP neighbors are not configured. Verify the
  CGW's `--bgp-asn` matches the on-prem device's BGP ASN. Verify the
  on-prem device has a BGP neighbor configured with the AWS-side inside
  IP (169.254.x.x).

### Route not propagating to TGW
- The TGW VPN attachment is not associated with a TGW route table, or
  propagation is not enabled. Call
  `associate-transit-gateway-route-table` and verify the route table
  has propagation enabled for the VPN attachment.
