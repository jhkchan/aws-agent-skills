# Baseline (no-skill) response: deregistration-delay-stranding

---

Your targets are stuck in draining state. This happens after instances
are replaced during an ASG refresh. The targets should eventually be
removed. You can try deregistering them manually or reducing the
deregistration delay timeout.

If they've been draining for 10 minutes, check if there are any
long-running connections keeping them alive. You might want to lower
the deregistration delay to speed things up.
