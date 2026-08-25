# Diagnostic commands — transit-gateway-deployer

Moved verbatim from SKILL.md for progressive disclosure. Load on demand.

**Live-account pre-flight checks (skip if doing offline architecture plan):**

1. Verify IAM permissions: `ec2:CreateTransitGateway*`, `AssociateTransitGatewayRouteTable`,
   `EnableTransitGatewayRouteTablePropagation`, `ec2:ModifyTransitGateway`,
   plus `ram:CreateResourceShare` for cross-account.
2. Verify each VPC subnet is `available` and AZ scope is consistent:
   `aws ec2 describe-subnets --subnet-ids <list>` returns `State=available`.
3. Verify no conflicting TGW ASN: each TGW in a peering pair must have
   a unique ASN. `aws ec2 describe-transit-gateways` returns ASNs.
4. For RAM shares: verify `aws ram get-resource-shares` shows the
   share `ACTIVE` and accepted by the consumer account.
5. For peering: verify the peer-region TGW exists in the peer account
   via `describe-transit-gateways --region <peer-region>`.
6. For Connect: verify the underlying VPC or Direct Connect gateway
   attachment is `available` in the same TGW.
7. For multicast: verify TGW `Options.MulticastSupport=enable`
   (cannot be added after creation).
