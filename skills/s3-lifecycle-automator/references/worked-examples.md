# Worked Examples — s3-lifecycle-automator

Moved verbatim from SKILL.md (progressive disclosure; load on demand). Sections keep their original headings.

### Worked example — REVIEW_REQUIRED, invalid min-days


```text
LIFECYCLE: invalid-transition-days
BUCKET: data-archive
POLICY:
  - Rule ID: archive-policy
  - Status: Enabled
  - Filter: all objects
TRANSITIONS:
  - Standard → Standard-IA: 15 days (min 30) — FAIL
  - Standard-IA → Glacier IR: 60 days (min 90) — FAIL
VERSIONING:
  - NoncurrentVersionExpiration: NOT CONFIGURED
VALIDATION:
  - Min-days check: FAIL (2 violations)
ENFORCEMENT:
  - Deployment: NOT DEPLOYED (validation blocked)
VERDICT: REVIEW_REQUIRED
GAP: Two min-days violations. (1) Standard→Standard-IA at 15 days: minimum is 30. API will accept but NEVER execute. Set to 30+. (2) Standard-IA→Glacier IR at 60 days: minimum is 90. Set to 90+. Also add NoncurrentVersionExpiration if versioning is enabled.
TEMPLATE: (corrected — set Days to 30 and 90 respectively, then re-deploy)
```
