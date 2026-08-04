# Baseline (no-skill) response: port-sweep-from-scanner

This file captures what a generic assistant produces WITHOUT the
guardduty-finding-severity-triage skill loaded — the contrast that proves
the skill identifies the authorized-scanner false-positive pattern.

---

This finding indicates that an EC2 instance is performing port sweeps
against multiple targets. The severity is 6.0 (medium).

Port sweeping is a reconnaissance technique used to identify open ports
on target systems. This could indicate that the instance has been
compromised, or it could be a legitimate security scanning activity.

You should investigate the source instance (i-0scanner01) to determine
whether the port sweep was authorized. If it was not authorized, you may
need to isolate the instance and investigate for compromise.
