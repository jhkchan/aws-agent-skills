# Baseline (no-skill) response: sg-blocking-health-check

---

Your ALB targets are showing unhealthy with connection failed. This
means the load balancer can't connect to your targets. The targets work
when you curl them locally, so the application is fine.

Check the security groups — make sure the target security group allows
inbound traffic from the ALB. Also check if the ALB subnets are
correct and if there are any network ACLs blocking traffic.

If the ALB was recently migrated, make sure the network path from the
new ALB subnets to the targets is still open.
