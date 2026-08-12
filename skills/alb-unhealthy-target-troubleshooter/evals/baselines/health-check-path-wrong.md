# Baseline (no-skill) response: health-check-path-wrong

This file captures what a generic assistant produces WITHOUT the
alb-unhealthy-target-troubleshooter skill loaded — the contrast that proves
the skill adds structure (deterministic VERDICT, layer identification,
evidence-backed root cause, symptom-to-layer triage).

---

Your ALB targets are unhealthy. This usually means the health check is
failing. Check if the application is running on the targets — SSH in and
verify the service is up. Also check the security group rules to make
sure port 8080 is open. You might also want to check the ALB configuration
to see if the health check settings look right.

If the app is running, try restarting the instances or redeploying the
application. Sometimes a fresh deploy fixes health check issues.
