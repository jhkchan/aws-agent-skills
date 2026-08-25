# Error handling — macie-data-classification-auditor

API failure and pagination handling moved verbatim from SKILL.md for progressive disclosure. Load on demand.

## Pre-flight — pagination and IAM notes

**Pagination and IAM notes:** `list-findings` and `list-classification-jobs`
return paginated results. Use `--max-results` and `--next-token` to
enumerate all entries. An `AccessDeniedException` on any Macie API call
usually means the Macie service-linked role is missing or the principal
lacks `macie2:*` permissions — emit `VERDICT: ERROR` with the IAM error
rather than guessing at the posture.
