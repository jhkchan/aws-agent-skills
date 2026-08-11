# Baseline (no-skill) response: plan-migration-tcp-listener-blocked

This file captures what a generic assistant produces WITHOUT the
clb-to-alb-migration-operator skill loaded.

---

To migrate your Classic Load Balancer to an Application Load Balancer:

1. Create the ALB with the same subnets and security groups.
2. Create a target group for port 8080.
3. Create an HTTPS listener on port 443 with the ACM cert.
4. Create a TCP listener on port 4242 for the game protocol.
5. Update DNS to point to the ALB.

This should move all traffic over.
