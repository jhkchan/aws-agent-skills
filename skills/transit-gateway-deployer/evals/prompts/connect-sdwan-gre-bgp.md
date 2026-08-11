# Eval prompt: connect-sdwan-gre-bgp

Design a deployment plan for a Transit Gateway with a Connect
attachment for SD-WAN integration. Emit the standard VERDICT block.

Requirements:

- TGW: prod-tgw-us-east-1 (ASN 64512, us-east-1, ACTIVE)
- Transport attachment: VPC attachment to vpc-0sdwan-transit
  (subnets subnet-0a1, subnet-0b1, subnet-0c1 in us-east-1a/b/c,
  all available)
- Connect attachment: Protocol=GRE, on top of the transport
  VPC attachment
- Connect peer:
  - PeerAddress=10.0.1.10 (private IP of the Cisco SD-WAN controller
    running in vpc-0sdwan-transit)
  - PeerAsn=65000
  - InsideCidr=169.254.0.0/29
  - BGP authentication: MD5 key configured (BgpAuthenticationKey)
- Route table: default route table; Connect attachment propagates
  its BGP-learned on-prem routes into the default route table
- The SD-WAN controller handles overlay encryption (DMVPN/IPsec);
  Connect is GRE transport only — NOT a VPN replacement

Existing-account context: vpc-0sdwan-transit has the Cisco SD-WAN
controller running at 10.0.1.10, with BGP configured for ASN 65000.
The TGW ASN 64512 is unique within the BGP peering pair. The
underlying VPC attachment is ACTIVE.
