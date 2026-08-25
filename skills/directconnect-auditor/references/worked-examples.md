# Worked Examples (load on demand) — Direct Connect Auditor

Secondary worked example moved verbatim from SKILL.md.
The primary pseudo-diversity worked example remains in SKILL.md.

---

## Worked example — malformed topology (ERROR) (moved from SKILL.md)

```text
CONNECTION: unknown
VERDICT: ERROR
REASON: Topology JSON is malformed — connection at index 2 is missing the
required `connectionId` field; cannot classify.
FINDINGS:
  - [ERROR] Connection at index 2 missing connectionId — skipped
REMEDIATION: Re-fetch with aws directconnect describe-connections --output json
and re-audit. If the issue persists, the API response was truncated mid-stream.
```
