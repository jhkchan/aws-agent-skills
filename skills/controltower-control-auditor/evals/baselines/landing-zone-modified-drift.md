# Baseline (no-skill) response: landing-zone-modified-drift

This file captures what a generic assistant produces WITHOUT the
controltower-control-auditor skill loaded — the contrast that proves the
skill adds structure (deterministic VERDICT, drift classification,
remediation ordering).

---

The landing zone shows drift detected. The AWSControlTowerBP StackSet has
3 drifted instances out of 10 — the template was modified outside Control
Tower. The AWSControlTowerSecurityResources StackSet also has 1 drifted
instance with a parameter mismatch.

The controls themselves are showing as SUCCEEDED and the SCPs match. The
Config recorder is enabled and the execution role is present.

You should remediate the drift by updating the landing zone or contacting
AWS support. Avoid upgrading the landing zone version while drift is
present as it may fail.
