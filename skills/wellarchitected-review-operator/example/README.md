# End-to-end usage scenario: wellarchitected-review-operator

A walkthrough showing the skill conducting a quarterly review of
the `checkout-service` workload — creating the workload with all
seven pillars (six base + Prosperity), answering the security
pillar with a HIGH risk-tier rationale, integrating Trusted
Advisor findings for cost optimization, drafting the improvement
plan, creating a milestone, and generating a PDF consolidated
report. This exercises Steps 1-10 of the review procedure.

## Input (user prompt)

> Create a Well-Architected Tool workload for `checkout-service`
> in `us-east-1`. Environment PRODUCTION. Review owner
> `payments-platform@example.com`. Lenses: `wellarchitected` and
> `wellarchitected-prosperity`. Account `111122223333`, regions
> `us-east-1` and `us-west-2`. All six base pillars plus
> Prosperity. Answer the security pillar — the workload has no
> automated rollback, mark the risky choice `HIGH_ISSUE` with
> rationale tied to the APP-SVC rollback SOP. Pull TA
> `LowUtilizationEC2Resources` findings as evidence for the cost
> optimization right-sizing question; do NOT auto-set the risk
> tier — let the operator confirm. Then create milestone
> `2026-Q3-baseline` and generate a PDF consolidated report.

## Skill output (first operation — create-workload)

```text
OPERATION: create-workload
VERDICT: READY
TARGET: checkout-service, wellarchitected + wellarchitected-prosperity, us-east-1
PRE_CHECKS:
  - [PASS] Caller identity 111122223333 has wellarchitected:CreateWorkload
  - [PASS] Prosperity lens wellarchitected-prosperity is imported into the account
  - [PASS] All six base pillar IDs valid
  - [PASS] No existing workload named checkout-service
STEPS:
  1. CONFIRM: About to create-workload checkout-service (PRODUCTION) in account 111122223333 region us-east-1. Lenses: wellarchitected, wellarchitected-prosperity. Pillars: operationalExcellence, security, reliability, performance, costOptimization, sustainability. Proceed? (yes/no)
  2. aws wellarchitected create-workload --workload-name checkout-service --description "Checkout microservice handling payment authorization and order capture" --environment PRODUCTION --review-owner payments-platform@example.com --lenses wellarchitected wellarchitected-prosperity --aws-regions us-east-1 us-west-2 --account-ids 111122223333 --pillar-ids operationalExcellence security reliability performance costOptimization sustainability --region us-east-1
POST_VERIFY:
  - (pending execution) expect WorkloadId returned; workload appears in list-workloads
STATE: pending — workload creation
NOTES:
  - Prosperity lens is associated at creation; no separate associate-lenses call needed.
  - Milestone should be created AFTER the review is complete (Step 6).
```

## Skill output (security pillar answer — HIGH risk)

```text
OPERATION: answer-pillar
VERDICT: READY
TARGET: workload-abc123, wellarchitected, security, us-east-1
PRE_CHECKS:
  - [PASS] Workload workload-abc123 exists
  - [PASS] Lens wellarchitected associated
  - [PASS] Caller has wellarchitected:UpdateAnswer
STEPS:
  1. CONFIRM: About to mark security question "How is rollback automated?" HIGH_ISSUE on workload-abc123. Rationale: no automated rollback — manual canary watch per APP-SVC rollback SOP. Proceed? (yes/no)
  2. aws wellarchitected update-answer --workload-id workload-abc123 --lens-alias wellarchitected --question-id <question-id> --choice-updates '{"<risky-choice-id>": {"Status": "NOT_SELECTED", "Reason": "RISK_GUIDANCE", "Notes": "No automated rollback — HIGH risk per APP-SVC rollback SOP"}}' --region us-east-1
POST_VERIFY:
  - (pending execution) get-answer returns ChoiceUpdates with HIGH_ISSUE reason
  - (pending execution) item appears in list-improvement-plans
STATE: pending — answer update
NOTES:
  - HIGH_ISSUE goes to top of improvement plan with remediation owner required.
```

## Skill output (TA integration — cost optimization)

```text
OPERATION: integrate-trusted-advisor
VERDICT: READY
TARGET: workload-abc123, wellarchitected, costOptimization, us-east-1
PRE_CHECKS:
  - [PASS] TA check LowUtilizationEC2Resources available
  - [PASS] Caller has trustedadvisor:GetCheckResult
  - [PASS] Workload workload-abc123 costOptimization pillar has right-sizing question
STEPS:
  1. aws trustedadvisor get-check-result --check-id LowUtilizationEC2Resources --region us-east-1
  2. CONFIRM: TA reports 3 underutilized EC2 instances. Surface as evidence in the right-sizing answer rationale. Risk tier selection: HIGH_ISSUE | MEDIUM_ISSUE | NO_ISSUE. Operator must confirm. (yes/no + risk tier)
  3. aws wellarchitected update-answer --workload-id workload-abc123 --lens-alias wellarchitected --question-id <question-id> --choice-updates '{"<right-sizing-gap-id>": {"Status": "NOT_SELECTED", "Reason": "RISK_GUIDANCE", "Notes": "TA LowUtilizationEC2Resources reports 3 underutilized instances — operator-confirmed risk tier"}}' --region us-east-1
POST_VERIFY:
  - (pending execution) get-answer returns ChoiceUpdates with TA evidence in Notes
STATE: pending — TA-informed answer update
NOTES:
  - TA is an evidence source, not an auto-answer. Operator confirmed the risk tier.
```

## What the skill caught that a generic assistant misses

1. **Lens import gate.** A generic assistant assumes the Prosperity
   lens is available. The skill verifies `list-lenses` and
   surfaces the gap with `import-lens` remediation.
2. **HIGH risk needs rationale + remediation owner.** A generic
   assistant marks a choice `HIGH_ISSUE` with no rationale. The
   skill requires workload evidence (APP-SVC rollback SOP) and a
   remediation owner.
3. **Milestone timing.** A generic assistant creates the milestone
   at workload creation. The skill defers milestone creation until
   AFTER the review is complete (Step 6) — milestones are
   point-in-time snapshots.
4. **TA is evidence, not answer.** A generic assistant auto-sets
   the risk tier from TA findings. The skill surfaces TA as
   evidence and CONFIRMS the risk tier with the operator.
5. **Pillar coverage in `--pillar-ids`.** A generic assistant
   omits pillars; the consolidated report comes back incomplete.
   The skill enumerates all six base pillar IDs at workload
   creation.
6. **PDF report format.** A generic assistant uses the default
   JSON output. The skill emits `--format PDF` for the
   executive-ready report.

## Slash-command invocation

```
/aws:operate-wellarchitected-review
```

Or via the orchestrator:

```
/aws:pipeline
You: "conduct quarterly review of checkout-service"
```

The orchestrator emits `[Phase: Operate | Skills routed:
wellarchitected-review-operator]` and hands off to this skill
for the VERDICT.

## Related scenarios

The same skill handles:

- **Create-workload** — name, environment, lenses, pillar IDs,
  account scope, review owner.
- **Answer-pillar** — risk-tier rationale per question,
  evidence-driven, with improvement plan derivation.
- **Generate-report** — JSON or PDF consolidated report with
  per-pillar risk distribution.
- **Create-milestone** — point-in-time snapshot AFTER the
  review is complete.
- **Integrate-trusted-advisor** — TA findings as evidence (not
  auto-answer) for cost, security, performance, reliability.
- **Improvement plan** — prioritized list with remediation
  owner per HIGH/MEDIUM item.
- **Lens lifecycle** — `import-lens`, `associate-lenses`,
  `disassociate-lenses`, custom lenses.
- **Cross-account sharing** — `create-workload-share`,
  recipient accepts via `accept-workload-share`.
