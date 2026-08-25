# Worked Examples — GuardDuty Finding Investigator

Secondary worked examples, moved verbatim from SKILL.md. Load on demand.

## Worked example — Recon:IAMUser/PortProbe (authorised scanner FP)

A Low-severity port-probe finding from `198.51.100.10` resolves to
FALSE_POSITIVE when the IP is the corporate Qualys scanner CIDR (verified
against `organization.org = "Qualys, Inc."` and the weekly scan window).
The block sets `LAYER: FALSE_POSITIVE`, recommends adding the CIDR to
the GuardDuty trusted IP list (`aws guardduty create-ip-set ... --activate`)
rather than suppressing the finding family, and confirms subsequent
weekly scans no longer produce `Recon:EC2/PortProbe` findings. The full
block format follows the STRICT output contract above; the key
suppression preference is **trusted IP list over archive filter** so
GuardDuty continues tracking the source.

