# Baseline (no-skill) response: nacl-missing-ephemeral-outbound

---

Your EC2 instance can't reach the API server. Since they're in the
same VPC, the routing should be fine. Check the security groups on
both sides — sg-api needs to allow inbound on 443, and sg-web needs
to allow outbound on 443.

If the security groups look fine, look at the NACLs. The default NACL
allows everything, but a custom NACL might be blocking return
traffic. Make sure the NACL allows the ephemeral port range
(1024-65535) for the return packets.
