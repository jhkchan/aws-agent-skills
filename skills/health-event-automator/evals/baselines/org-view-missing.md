# Baseline (no-skill) response: org-view-missing

This file captures what a generic assistant produces WITHOUT the
health-event-automator skill loaded.

---

To get Health event coverage across your 50-account org, you should
deploy your EventBridge rules to all 50 accounts. You can use
CloudFormation StackSets from your management account to roll out the
rules consistently.

Alternatively, you can enable organizational view and delegate an
administrator account to see aggregated Health events centrally.

Make sure each account has the right IAM roles for the responders.

---

Notes on what the baseline misses:

- Treats per-account StackSet deployment as the primary path, missing
  that org view + delegated admin is the canonical centralization
  pattern (single rule vs 50 rules).
- Does NOT flag that 45 of 50 accounts have ZERO coverage today as a
  CRITICAL gap.
- Does NOT specify that enable-health-service-access-for-organization
  must run from the management account first.
- Does NOT flag the missing scheduledChange automation.
- Does NOT flag the missing replay test or poller fallback.
- Does NOT recommend a single org-level rule in the delegated admin's
  default bus as the centralization mechanism.
