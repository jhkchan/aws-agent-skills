# Advanced Patterns — Well-Architected Review Operator

Load-on-demand deep dives moved verbatim from SKILL.md: reasoning framework, improvement-plan remediation mapping, labs wiring, edge-case catalog, recent AWS features, and expert risk-tier heuristics.

## Reasoning framework (why the review order matters)
Operating a Well-Architected review has **dependency and
ordering constraints** that make the procedure non-trivial.
Skipping or misordering causes silent gaps — answers don't
persist, the report is empty, or milestones capture the wrong
snapshot:

1. **Workload FIRST with lens selection** — `create-workload`
   provisions the review container and binds the lenses
   (Well-Architected Framework + optional specialty lenses like
   SaaS, FTR, Healthcare). Adding a lens later via
   `import-lens` requires the lens to be enabled in the account.
2. **Environment + description drive downstream** — the
   workload `Environment` (`PRODUCTION` | `PREPRODUCTION` |
   `OTHER`) shapes risk tolerance interpretation. A `PREPROD`
   workload may accept MEDIUM risks a `PRODUCTION` workload
   would not.
3. **Lens availability is account-scoped** — specialty lenses
   (SaaS, FTR, Healthcare, etc.) must be enabled in the account
   via `import-lens`. Referencing an un-imported lens produces
   `ResourceNotFoundException` at update-answer time.
4. **Answer risk-tier is opinion, not metric** — the
   Well-Architected Tool stores `ChoiceUpdates` with a risk
   tier (`HIGH_ISSUE` / `MEDIUM_ISSUE` / `NO_ISSUE`). The
   skill answers with rationale tied to actual workload state;
   a generic answer with no workload evidence is rejected by
   the operator as invalid.
5. **Improvement plan items are derived from HIGH and MEDIUM
   answers** — the consolidated report aggregates every
   `HIGH_ISSUE` and `MEDIUM_ISSUE` answer into the improvement
   plan. Answering with `NO_ISSUE` removes the item from the
   plan silently.
6. **Milestones snapshot at write time** — a milestone captures
   the current state of answers and improvement plan at the
   moment of `create-milestone`. Subsequent answer updates do
   NOT back-propagate. Create the milestone AFTER the review
   is complete.
7. **Trusted Advisor checks supplement, not replace** — TA
   findings map to specific Well-Architected questions
   (cost optimization, security, performance). Importing TA
   findings pre-populates evidence but does not auto-answer.
8. **The Prosperity pillar (2025) is opt-in via lens import**
   — the Prosperity pillar is delivered as a specialty lens,
   not part of the default Well-Architected Framework. Import
   the lens before answering Prosperity questions.

## Step 5 — improvement plan remediation mapping
Each improvement plan item references the question, the
choice that introduced the risk, and the guidance text from
AWS. The skill augments each item with a concrete remediation
link:
- For operational excellence gaps, link to the
  operational excellence lab.
- For security gaps, link to the security lab and the
  Security Hub control that maps to the question.
- For cost optimization gaps, link to the cost optimization
  lab and the Compute Optimizer / Cost Optimization Hub
  recommendation.

## Step 8 — Well-Architected Labs wiring
Well-Architected Labs (https://www.wellarchitectedlabs.com)
provides hands-on remediation runbooks. The skill references
the relevant lab for each improvement plan item:
- Operational Excellence: Reliability by Workload category.
- Security: Security pillar labs.
- Reliability: Resiliency labs (e.g., Resiliency of
  Workloads).
- Performance: Performance Efficiency pillar labs.
- Cost Optimization: Cost Optimization labs.
- Sustainability: Sustainability labs.
- Prosperity: Value-stream labs (2025).

## Edge-case handling
- **Lens not in account:** `update-answer` with an un-imported
  lens alias returns `ResourceNotFoundException`. Run
  `import-lens` first, then `associate-lenses` to attach to
  the workload.
- **Workload `Environment` mismatch:** a `PREPRODUCTION`
  workload accepts MEDIUM risks that a `PRODUCTION` workload
  would not. Re-assess risk tolerance when promoting.
- **Answer did not persist:** the most common cause is
  `ChoiceUpdates` referencing a wrong `ChoiceId`. Verify the
  choice ID via the lens question before `update-answer`.
- **Milestone captured wrong state:** a milestone is a
  point-in-time snapshot. If answers changed after the
  milestone, create a new milestone. Milestones cannot be
  updated.
- **Consolidated report empty:** no answers recorded for the
  target pillar. Verify `list-answers` returns entries for
  the pillar before generating the report.
- **Cross-account share rejected:** the recipient account must
  accept the share via `accept-workload-share`. The workload
  does NOT appear in the recipient account until accepted.
- **Prosperity pillar not appearing:** the Prosperity lens
  must be imported AND associated with the workload. Verify
  via `list-lenses --workload-id <id>`.
- **Trusted Advisor check returning no result:** some TA
  checks require opt-in or have been migrated to AWS
  Resilience Hub / Security Hub. Check `describe-checks` for
  availability.

## Recent AWS features (2024-2026)
- **Prosperity pillar (2025):** a new pillar delivered as a
  specialty lens (`wellarchitected-prosperity`) covering
  sustainability of growth, customer-centric measures, and
  value-stream health. Opt-in via `import-lens`. Not part of
  the default Well-Architected Framework.

- **Well-Architected Tool API expansion (2024-2025):** the
  API now supports `list-improvement-plans`,
  `get-consolidated-report` with `--format PDF`,
  `--include-shared-resources`, and per-pillar filtering on
  `list-answers`. Programmable review lifecycle is now
  first-class.

- **Trusted Advisor integration via AWS Health Aware (2024-2025):**
  the Well-Architected Tool consumes Trusted Advisor findings
  via the AWS Health API, automatically suggesting risk-tier
  selections for cost, security, performance, and reliability
  questions.

- **Well-Architected Labs automation (2024-2026):** the labs
  site (wellarchitectedlabs.com) ships Infrastructure-as-Code
  runbooks (CDK + Terraform) for each pillar's common gaps.
  The skill references the relevant lab per improvement plan
  item.

- **Custom lenses (2024-2025):** customers can author custom
  lenses and publish to the AWS Well-Architected Tool. Custom
  lenses appear alongside AWS-authored lenses in `list-lenses`.

- **Cross-account review sharing (2024-2025):**
  `create-workload-share` enables reviewer or contributor
  access across accounts. The recipient must accept via
  `accept-workload-share`.

- **Consolidated Reports PDF (2024-2025):** the
  `get-consolidated-report` API now supports `--format PDF`
  for executive-ready reports with per-pillar risk distribution
  charts.

- **Integration with AWS Resilience Hub (2024-2025):** for
  reliability pillar reviews, Resilience Hub policy assessments
  can be imported as evidence via the
  `ImportResiliencePolicy` integration.

## Expert heuristic — risk-tier strategy
- **Default to evidence-driven answers.** Every answer must
  cite workload evidence (deployment topology, observability
  coverage, on-call runbooks). A generic answer is invalid.
- **HIGH risks need a remediation owner.** Every `HIGH_ISSUE`
  should be paired with an owner and a target date in the
  improvement plan. The skill surfaces this as a follow-up.
- **MEDIUM risks are acceptable with rationale.** A
  `MEDIUM_ISSUE` is acceptable for a `PREPRODUCTION`
  workload. Promote to `HIGH_ISSUE` when the workload moves
  to `PRODUCTION`.
- **Use TA findings as supporting evidence, not as the
  answer.** TA findings inform the rationale; the operator
  confirms the risk-tier based on the workload's tolerance.
- **The Prosperity pillar (2025) is a specialty lens.** Import
  the lens and associate with the workload before answering
  Prosperity questions.
- **Milestones mark review cycles.** Use a date-based naming
  convention (`2026-Q3-baseline`). Create one milestone per
  review cycle, not per answer.
- **Specialty lenses cross-reference.** The Security lens and
  the FTR lens overlap on IAM questions. Answer the question
  once per lens — the consolidated report shows both lens
  findings.
