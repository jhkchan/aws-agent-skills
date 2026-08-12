# Baseline (no-skill) response: tgw-appliance-mode-disabled

---

Your inspection VPC is dropping flows intermittently. The pattern
correlates with the source AZ, which suggests the firewall is only
seeing one direction of the flow for some traffic. Check the firewall
rules to make sure they allow the traffic from both AZs.

You might also want to deploy the firewall in multiple AZs so it can
handle traffic regardless of where the source is. Or check the TGW
route tables to make sure return traffic goes through the inspection
VPC.
