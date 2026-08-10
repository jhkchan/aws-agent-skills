# Baseline (no-skill) response: 502-target-sg-blocks-alb

This file captures what a generic assistant produces WITHOUT the
alb-5xx-troubleshooter skill loaded — the contrast that proves the skill
adds structure (deterministic VERDICT, layer identification,
evidence-backed root cause, error-code-driven probe order).

---

A 502 from your ALB means the backend is not responding properly. Since
your targets show as healthy, the issue might be with the connection
between the ALB and the targets. Check the security groups on your
targets to make sure they allow traffic from the ALB.

Also check that the target port in your target group matches the port
your application is actually listening on. If the ALB is trying to
connect on a port that's not open, you'll get a 502.
