# Baseline (no-skill) response: recon-portprobe-authorized-scanner

This file captures what a generic assistant produces WITHOUT the
guardduty-finding-investigator skill loaded — the contrast that proves
the skill adds structure (deterministic VERDICT, layer identification,
evidence-backed root cause, finding-type-driven probe order).

---

A low-severity Recon PortProbe finding usually means someone is scanning
your environment. If you recognize the source IP, you can archive the
finding in GuardDuty. Otherwise just leave it — Low severity findings
aren't urgent.

You can suppress all PortProbe findings if they're too noisy. Use the
GuardDuty console to filter on type equals Recon:EC2/PortProbe and
archive. That should quiet things down.
