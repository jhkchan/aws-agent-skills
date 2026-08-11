# Baseline (no-skill) response: connect-sdwan-gre-bgp

This file captures what a generic assistant produces WITHOUT the
transit-gateway-deployer skill loaded — contrast proves the skill
adds structure around the dual-layer Connect model (transport +
Connect + peer), the "not a VPN replacement" constraint, and
BGP ASN uniqueness.

---

Here's a plan to set up a Connect attachment for your SD-WAN.

The topology will:
- Use the vpc-0sdwan-transit VPC attachment as transport
- Tunnel GRE to the Cisco SD-WAN controller at 10.0.1.10
- Exchange BGP routes so VPCs can reach on-prem branches

Steps:

1. Create the Connect attachment on the transport VPC attachment.
2. Create the Connect peer with the Cisco controller's IP and BGP ASN.

Commands:

```
aws ec2 create-transit-gateway-connect \
  --transport-transit-gateway-attachment-id <transport-attach-id> \
  --options Protocol=gre
aws ec2 create-transit-gateway-connect-peer \
  --transit-gateway-attachment-id <connect-attach-id> \
  --peer-address 10.0.1.10 \
  --bgp-options PeerAsn=65000 \
  --inside-cidr-cidrs 169.254.0.0/29
```

The Connect peer should establish a GRE tunnel and BGP session
with your SD-WAN controller. Let me know if you need help with
the route table propagation.
