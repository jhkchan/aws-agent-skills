# Baseline (no-skill) response: cryptocurrency-ec2-true-positive

This file captures what a generic assistant produces WITHOUT the
guardduty-finding-investigator skill loaded — the contrast that proves
the skill adds structure (deterministic VERDICT, layer identification,
evidence-backed root cause, finding-type-driven probe order).

---

Your EC2 instance has a crypto mining finding. You should isolate the
instance and check what's running on it. Look at the process list and
see if there's a miner running. The high CPU is a strong indicator that
something is mining on the box.

I'd terminate the instance to be safe, or at least stop it. Then check
your other instances for the same issue. You may want to add a WAF rule
to block the mining pool domain.
