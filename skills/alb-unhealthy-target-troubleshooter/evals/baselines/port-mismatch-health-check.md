# Baseline (no-skill) response: port-mismatch-health-check

---

Your targets are unhealthy with connection failed. The application
listens on port 8080, so make sure the health check is configured to
use the right port. Check the target group settings in the AWS console.

Also verify that the security group allows traffic on the health check
port. If the SG allows both 80 and 8080, the issue is likely the health
check port setting on the target group.

Try changing the health check port to 8080 or to "traffic-port" and
see if the targets become healthy.
