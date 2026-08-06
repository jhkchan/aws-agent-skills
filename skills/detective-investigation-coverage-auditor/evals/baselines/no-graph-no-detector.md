# Baseline (no-skill) response: no-graph-no-detector

This file captures what a generic assistant produces WITHOUT the
detective-investigation-coverage-auditor skill loaded — the contrast that
proves the skill adds structure (deterministic VERDICT, enumerated FINDINGS,
specific remediation, investigation-readiness reasoning).

---

Amazon Detective is not enabled in the us-east-1 region. You should enable
it by running `aws detective create-graph` in that region. GuardDuty also
appears to be disabled, so you will need to set that up first for Detective
to be useful.

Without Detective, you have no behavior graph for security investigations.
