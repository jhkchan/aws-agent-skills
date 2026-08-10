# Baseline (no-skill) response: 502-vpclink-unhealthy-target

This file captures what a generic assistant produces WITHOUT the
apigateway-5xx-troubleshooter skill loaded — the contrast that proves
the skill adds structure (deterministic VERDICT, layer identification,
evidence-backed root cause, error-code-driven probe order).

---

A 502 error from your VPC Link integration means the backend is returning
an error. Check your NLB and target group to make sure the targets are
healthy. You might need to look at the health check configuration and
make sure the backend instances are running and responding correctly.

Also verify that the security groups allow traffic from the NLB to your
targets on the correct port.
