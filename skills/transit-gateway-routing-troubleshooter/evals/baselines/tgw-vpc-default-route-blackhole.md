# Baseline (no-skill) response: tgw-vpc-default-route-blackhole

---

Your ping from VPC-A to VPC-B isn't getting a reply. The TGW route
tables look fine and the forward path works. The problem is likely a
security group or NACL blocking the return traffic.

Check the security group on i-bbb to make sure it allows inbound ICMP
from VPC-A's CIDR. Also verify the NACLs in VPC-B are not blocking
the ephemeral port range for the reply.
