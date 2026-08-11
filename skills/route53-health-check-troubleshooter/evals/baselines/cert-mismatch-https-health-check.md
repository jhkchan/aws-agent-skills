# Baseline (no-skill) response: cert-mismatch-https-health-check

This file captures what a generic assistant produces WITHOUT the
route53-health-check-troubleshooter skill loaded — the contrast that
proves the skill adds structure (deterministic VERDICT, layer
identification, evidence-backed root cause, certificate-mismatch
awareness).

---

Your Route 53 health check is reporting unhealthy. Since the endpoint
is reachable from the VPC via curl -k, the issue is likely that Route
53 can't reach the endpoint or there's a configuration problem. Check
the health check type and port — make sure they match what your server
is listening on.

If the endpoint is behind an ALB, make sure the ALB security group
allows traffic from Route 53 health checker IPs. You might also want
to try switching to a TCP health check instead of HTTPS to rule out
certificate issues.
