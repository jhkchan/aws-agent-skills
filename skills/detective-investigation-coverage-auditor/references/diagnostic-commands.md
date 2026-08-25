# Diagnostic Commands (load on demand) — Detective Investigation Coverage Auditor

Live-account pre-flight checks and pre-flight safety checks moved verbatim from SKILL.md.
The primary worked example and classification steps remain in SKILL.md.

---

## Live-account pre-flight checks (moved from SKILL.md)

**Live-account pre-flight checks (skip if doing offline config audit):**
1. Verify the caller's identity has `detective:ListGraphs` — most read-only
   auditor roles CAN, but member accounts (not the admin) cannot list the
   graph they belong to. Run from the Detective administrator account.
2. Verify GuardDuty is reachable: `aws guardduty list-detectors`. A
   successful call confirms GuardDuty is enabled in the region — Detective
   cannot function without it.
3. For Organizations environments, verify the caller is the delegated
   admin account: `aws detective describe-organization-configuration`.
   Non-admin accounts see empty results even when the org graph is healthy.

---

## Pre-flight safety checks (run before any remediation CLI) (moved from SKILL.md)

- **MANDATORY CONFIRMATION GATE.** Before any state-changing operation
  (create-members, delete-graph, enable-organization-admin-account,
  start-monitoring-member, batch-enable-disable-data-source-packages),
  the auditor MUST emit:
  `CONFIRM: About to <action> on graph <arn> in account <account>. This
  affects <consequence>. Proceed? (yes/no)`
  Do NOT execute the CLI command until the operator confirms.

- **Graph deletion is irreversible.** Before recommending or executing
  `aws detective delete-graph`, capture the graph ARN, member list, and
  data-source states as a baseline. There is no backup or rollback —
  all historical investigation data is permanently lost.

- **Member re-invitation does not preserve data.** If a member was
  ACCEPTED_BUT_DISABLED and you re-enable it, the member resumes
  ingestion from the current point forward — there is no backfill of
  data from the disabled period. The gap is permanent in the graph.

- **Delegated admin designation is one-time.**
  `aws detective enable-organization-admin-account` can only designate
  ONE admin account per org. Changing the admin requires disabling the
  current admin first, which deletes the org-wide graph. Plan the
  designation carefully.

- **Verify the caller is the admin account** before running member
  operations. Member accounts cannot invite other members, enable data
  sources, or configure the org graph. Running admin operations from a
  member account returns `AccessDenied`.

- Prefer additive changes (re-send invitations, enable data-source
  packages) over destructive changes (remove members, delete graph).
  Additive changes are reversible and do not risk losing historical
  investigation data.
