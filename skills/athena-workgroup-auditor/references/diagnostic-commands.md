# Diagnostic Commands — Athena Workgroup Auditor

Load-on-demand pre-flight and diagnostic CLI moved verbatim from SKILL.md.

## Pre-flight: account-wide sweep and live-account checks

**Account-wide sweep note (pagination):** `aws athena list-work-groups`
returns at most 50 workgroups per page. Use `--next-token` from the
prior `NextToken` to page through; iterating only the first page
silently skips stale workgroups (the ones most likely to be
unenforced). For each workgroup, also page
`aws athena list-named-queries --work-group <name>` (50/page) and
`aws athena list-query-executions --work-group <name>` (50/page) —
both silently truncate.

**Live-account pre-flight checks (skip if doing offline config audit):**
1. Verify the caller can run `athena:GetWorkGroup` — read-only auditor
   roles usually can, but cross-account workgroup audits require the
   workgroup to be shared via Resource-based policy (rare). Surface
   AccessDenied BEFORE the operator approves any remediation.
2. Confirm which CloudTrail trail is capturing Athena events in the
   workgroup's region. Athena management events (`StartQueryExecution`,
   `StopQueryExecution`, `CreateNamedQuery`) are on by default; Athena
   **data events** (`BatchGetQueryExecution`, `GetQueryExecution`,
   `GetQueryResults`) must be explicitly enabled on the trail's
   `AdvancedEventSelectors`. Without data events, post-45-day forensics
   have no signal.
3. Snapshot `aws athena get-work-group --work-group <name>` BEFORE any
   `UpdateWorkGroup` call — workgroup configs are not versioned and
   there is no rollback. The CLI returns the full Configuration block;
   save it to a file for diff/recovery.
