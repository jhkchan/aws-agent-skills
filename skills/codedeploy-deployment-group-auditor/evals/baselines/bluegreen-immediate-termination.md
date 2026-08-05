# Baseline (no-skill) response: bluegreen-immediate-termination

This file captures what a generic assistant produces WITHOUT the
codedeploy-deployment-group-auditor skill loaded — the contrast that proves
the skill adds structure (deterministic VERDICT, enumerated FINDINGS,
specific remediation, deployment-safety reasoning).

---

This is a blue/green deployment group with rollback and alarms enabled.
The deployment config is OneAtATime. Blue instances are terminated
immediately (0 minutes) after the green deployment succeeds.

You should consider increasing the termination wait time to give yourself
a buffer to verify the green fleet is working correctly before the blue
instances are removed.
