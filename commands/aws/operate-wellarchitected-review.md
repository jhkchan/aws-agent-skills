---
description: Operates AWS Well-Architected Tool reviews end-to-end — creates workloads, runs pillar reviews (operational excellence, security, reliability, performance, cost optimization, sustainability, Prosperity), answers questions with risk-tier rationale, generates consolidated reports and improvement plans, creates milestones, and integrates with Trusted Advisor and Well-Architected Labs. Emits READY | BLOCKED | COMPLETED with the exact CLI sequence and post-verification.
nl_triggers:
  - "well-architected tool"
  - "well architected review"
  - "war review"
  - "workload review"
  - "well architected workload"
  - "create workload wellarchitected"
  - "pillar review"
  - "operational excellence pillar"
  - "security pillar"
  - "reliability pillar"
  - "performance efficiency pillar"
  - "cost optimization pillar"
  - "sustainability pillar"
  - "prosperity pillar"
  - "improvement plan"
  - "well architected milestone"
  - "consolidated report"
  - "trusted advisor integration"
  - "wellarchitected labs"
  - "well architected lens"
  - "wellarchitected prosperity"
routes_to: wellarchitected-review-operator
---

# /aws:operate-wellarchitected-review

Invoke the `wellarchitected-review-operator` skill to plan or
execute a Well-Architected review operation.

Read the skill at
`skills/wellarchitected-review-operator/SKILL.md` and follow its
procedure to plan and execute the operation.

## When to use

- Create a Well-Architected Tool workload (name, environment,
  lenses, pillar IDs, account scope, review owner).
- Answer pillar questions (operational excellence, security,
  reliability, performance efficiency, cost optimization,
  sustainability, Prosperity) with risk-tier rationale.
- Generate a consolidated report (JSON or PDF) with per-pillar
  risk distribution.
- Draft an improvement plan with remediation owners per
  HIGH/MEDIUM item.
- Create a milestone AFTER the review is complete.
- Integrate Trusted Advisor findings as evidence (not
  auto-answer) for cost, security, performance, reliability.
- Import and associate specialty lenses (SaaS, FTR,
  Healthcare, Prosperity).
- Share a workload cross-account (`create-workload-share`,
  recipient accepts via `accept-workload-share`).

## Invocation

```
/aws:operate-wellarchitected-review <workload / lens / pillar / milestone / symptom>
```

The skill will:

1. Capture the operation target (operation type, workload id,
   lens alias, pillar id, milestone name, region).
2. Run pre-flight: confirm workload existence, lens
   availability, pillar coverage, caller permissions, TA check
   availability.
3. Emit the CLI sequence with all flags populated
   (`create-workload`, `update-answer`,
   `get-consolidated-report`, `create-milestone`,
   `associate-lenses`, `import-lens`, `create-workload-share`).
4. For answer-pillar: emit the `ChoiceUpdates` map with
   risk-tier rationale citing workload evidence.
5. For generate-report: emit `get-consolidated-report --format
   JSON|PDF` with the lens filter.
6. For create-milestone: emit `create-milestone` AFTER the
   review is complete.
7. For TA integration: surface TA findings as evidence in the
   answer rationale, then CONFIRM the risk-tier with the
   operator.
8. Emit the standard VERDICT block.

## Output shape

```text
OPERATION: <create-workload | answer-pillar | generate-report | create-milestone | integrate-trusted-advisor | describe>
VERDICT: READY | BLOCKED | COMPLETED
TARGET: <workload-id, lens, pillar, region>
PRE_CHECKS:
  - [PASS] <check description>
  - [FAIL] <check description> — <reason>
STEPS:
  1. CONFIRM: About to <operation> on <workload/lens/pillar>. Proceed? (yes/no)
  2. <exact CLI command with all flags populated>
POST_VERIFY:
  - [PASS] <verification description>
  - [FAIL] <verification description> — <reason>
STATE: <workload review state>
NOTES: <pillar coverage, lens availability, TA integration caveats>
```

## Pre-flight

The skill requires the operation type and the workload /
lens / pillar identifiers. If only a partial configuration is
provided, the skill runs `aws wellarchitected list-workloads`
and `aws wellarchitected list-lenses` to surface existing
resources, or emits `BLOCKED` with the list of missing inputs
for a new operation.

## Pipeline integration

This skill operates in **Phase 3 (Operate)** of the CloudOps
pipeline. The output feeds into governance pipelines and
downstream auditor skills (e.g., the
`wellarchitected-workload-auditor` skill which validates
review completeness, and the
`trustedadvisor-check-auditor` skill which closes the loop on
TA findings cited in answers).

## Example

```
You: /aws:operate-wellarchitected-review

     Conduct a quarterly review of checkout-service
     (id workload-abc123) in us-east-1. Lenses:
     wellarchitected + wellarchitected-prosperity. Answer the
     security pillar — no automated rollback, mark HIGH_ISSUE
     with rationale tied to the APP-SVC rollback SOP. Pull TA
     LowUtilizationEC2Resources findings as evidence for the
     cost optimization right-sizing question; do NOT auto-set
     the risk tier. Then create milestone 2026-Q3-baseline and
     generate a PDF consolidated report. Account: 111122223333.

Skill:
  OPERATION: answer-pillar
  VERDICT: READY
  TARGET: workload-abc123, wellarchitected, security, us-east-1
  PRE_CHECKS:
    - [PASS] Workload workload-abc123 exists
    - [PASS] Lens wellarchitected associated
    - [PASS] Caller has wellarchitected:UpdateAnswer
  STEPS:
    1. CONFIRM: About to mark security question HIGH_ISSUE on workload-abc123. Proceed? (yes/no)
    2. aws wellarchitected update-answer --workload-id workload-abc123 --lens-alias wellarchitected --question-id <id> --choice-updates '{"<risky-choice-id>": {"Status": "NOT_SELECTED", "Reason": "RISK_GUIDANCE", "Notes": "No automated rollback — HIGH risk per APP-SVC rollback SOP"}}' --region us-east-1
  POST_VERIFY:
    - (pending) get-answer returns ChoiceUpdates with HIGH_ISSUE
    - (pending) item appears in list-improvement-plans
  STATE: pending — answer update
  NOTES: HIGH_ISSUE goes to top of improvement plan with remediation owner required.
```

## References

- Skill: `skills/wellarchitected-review-operator/SKILL.md`
- Reference: `skills/wellarchitected-review-operator/references/review-cli-commands.md`
- Reference: `skills/wellarchitected-review-operator/references/pillar-question-bank.md`
- AWS docs: https://docs.aws.amazon.com/wellarchitected/latest/userguide/intro.html
