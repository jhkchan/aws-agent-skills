# Error Handling — Audit Manager Assessment Auditor

Load-on-demand error handling moved verbatim from SKILL.md.

## Pre-flight — malformed snapshot and API-failure ERROR blocks

**If the assessment metadata block is malformed** (missing `status`,
missing `controlSets`, missing `scope`), output:

```text
ASSESSMENT: <id>
VERDICT: ERROR
REASON: Assessment snapshot is missing required fields (status/controlSets/scope) — cannot classify.
REMEDIATION: Re-fetch with `aws auditmanager get-assessment --assessment-id <id> --region <r>` and re-audit.
```

**If an Audit Manager API call fails** during a live audit
(`AccessDeniedException`, `ThrottlingException`, `ResourceNotFoundException`,
or any non-2xx), do NOT guess a verdict from partial data. Emit:

```text
ASSESSMENT: <id>
VERDICT: ERROR
REASON: <API name> returned <errorClass>: <message> — audit aborted.
REMEDIATION: <permission/quota/retry hint, e.g. "grant auditmanager:GetAssessment"
  or "request Service Quota increase for auditmanager:ListAssessments per account">.
```

## API failure, pagination fallback, and partial-success fan-out

- **API failure / pagination fallback.** `list-assessments`,
  `list-delegations`, and `list-assessment-control-insights-by-control-domain`
  are paginated — a single call without `--next-token` truncates large
  estates. Always loop on `nextToken`. If a `ThrottlingException` or
  `AccessDeniedException` returns on `get-assessment`, emit `VERDICT: ERROR`
  with the API error class (do NOT guess a verdict from a missing snapshot),
  and re-route the operator to check IAM `auditmanager:GetAssessment` and
  the account Service Quota. An empty `list-accounts` response from
  Organizations is *not* "no members" — it usually means the caller is in
  a member account, not the management account; treat as "scope cannot be
  determined" per Step 1d, not as "single-account org".

- **Partial-success API fan-out (Config OK in account A, CloudTrail
  AccessDenied in account B).** When verifying data sources across the
  per-account × per-region perimeter, some calls will succeed while
  others fail with `AccessDeniedException` (cross-account role not
  assumable in a member), `ThrottlingException` (account-level limiter),
  or `OperationNotPermittedException`. Handle explicitly:
  1. Emit one scoped finding per failing call, e.g.:
     `[UNVERIFIED] Config recorder status for account 333 in eu-west-1
     could not be retrieved (AccessDeniedException) — treat as suspected
     collection break (Step 1b).`
  2. Compute NOT_ASSESSED% on the verified subset ONLY.
  3. In REASON, append: `verdict confidence reduced — <X/Y> accounts
     unverified (<Z>%).`
  4. If unverified scope > 25% of the in-scope perimeter, escalate the
     VERDICT to `INCOMPLETE_EVIDENCE` regardless of the visible
     NOT_ASSESSED ratio — the worst account is statistically likely to
     be in the unverified set.
  5. NEVER silently drop the failing calls and classify on the visible
     subset as if it were the full estate — averaging over a partial
     perimeter hides the worst accounts.
