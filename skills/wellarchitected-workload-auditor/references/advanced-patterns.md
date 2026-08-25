# Advanced Patterns — Well-Architected Workload Auditor

Load-on-demand deep dives moved verbatim from SKILL.md: Step-0 classification behaviors, WA Tool API internals, and recent AWS features.

- **`effectiveReviewDate` uses milestones, not just `LastUpdated`.** A
  workload's `LastUpdated` reflects metadata edits (name, description, lenses).
  Milestone `RecordedAt` reflects review-answer progression. Always use
  `max(LastUpdated, most-recent milestone.RecordedAt)` for staleness.

- **`RiskCounts` at the workload level is an aggregate across ALL pillars.**
  The `describe-workload` API returns a single `RiskCounts` map — it does NOT
  break down by pillar. You must call `list-answers --pillar-id <pillar>` per
  pillar and aggregate client-side to know whether HIGH_RISK issues are in
  `security` (urgent) or `costOptimization` (less urgent).

- **Security pillar is zero-tolerance.** One HIGH_RISK in `security` is more
  dangerous than five in `costOptimization` — security risks are exploitable
  attack vectors. Rule 2a triggers on `security.HIGH_RISK > 0`; other pillars
  need total > 5.

- **`UNANSWERED > 50%` means the review was abandoned.** The operator may
  have answered easy questions and skipped hard ones, producing a falsely
  optimistic risk picture. Classify as STALE_REVIEW — the data is not
  trustworthy enough to evaluate HIGH_RISK or CONFIG_GAP.

## Deep reference: WA Tool API internals

### Non-obvious WA Tool behaviors (extended)
- **Milestones are immutable once created.** You cannot delete or edit a
  milestone — `RecordedAt` and `WorkloadSummary` are frozen. This makes
  milestones the authoritative audit trail and the only rollback reference.

- **`list-answers` requires `--pillar-id` as a mandatory parameter.** There
  is no "list all answers" API call. The six pillar IDs are fixed:
  `security`, `reliability`, `performance`, `costOptimization`,
  `operationalExcellence`, `sustainability`.

- **`list-workloads` and `list-milestones` both cap at 50 per page.** For
  account-wide sweeps, drain `NextToken` to completion.

- **Workload ID is a 32-character hex string**, not an ARN. All WA Tool API
  calls take `--workload-id <hex>`.

- **Lens aliases are lowercase identifiers, not display names.** The default
  Framework lens is `wellarchitected`. Additional lenses appear as aliases
  or custom lens ARNs.

- **`ImprovementPlan` from `describe-workload` mixes manual and
  tool-generated items.** The API does not distinguish human-committed
  actions from auto-generated gap-report suggestions. A non-zero
  `ImprovementPlanItems` count does NOT mean a human reviewed each item —
  check whether items carry a `GapReport` origin before citing the count as
  evidence of an active remediation plan.

- **Lens versioning silently remaps answer risk.** If a lens is upgraded
  after the review, `list-answers` returns answers against the new version.
  `QuestionId` is stable across versions, but `SelectedChoices` may map to
  different risk levels. A review that was OK under lens v1 may show new
  HIGH_RISK under v2 without any architectural change.

- **`list-check-summaries` returns empty (not error) when no AppRegistry
  association exists.** Automated Trusted Advisor checks require a linked
  CloudFormation stack or AppRegistry application. An empty result does NOT
  validate the review answers — it means the cross-check infrastructure is
  not connected. Do not treat "no failing checks" as evidence of correctness
  when the association is absent.

## Recent AWS features (2024-2026)
- **Well-Architected Framework updates (2024-2025):** AWS published updates to the Well-Architected Framework including sustainability pillar refinements and machine learning lens updates. Auditors should verify that reviews use the latest framework version and that new best-practice questions are addressed.
- **Custom lenses GA (2024):** Custom lenses allow organizations to define their own Well-Architected review questions. Auditors should verify that custom lenses are versioned, documented, and reviewed for alignment with organizational policies.
- **Well-Architected Tool API enhancements (2024-2025):** Expanded API support for programmatic workload creation, milestone management, and report generation. Auditors should verify that API-driven workload updates are tracked and that milestone API calls are logged in CloudTrail.
- **Integration with AWS Resilience Hub (2024):** Well-Architected Tool now integrates with Resilience Hub for reliability pillar deep-dives. Auditors should verify that reliability findings from Resilience Hub are incorporated into WA reviews.
