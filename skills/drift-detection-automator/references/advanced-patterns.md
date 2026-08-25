# Advanced Patterns (load on demand) — Drift Detection Automator

Step-0 expert knowledge, Appendix A/B, the GitHub Actions workflow, expert heuristics, and 2024-2026 feature changes, moved verbatim from SKILL.md.


---

## Step 0: Expert knowledge — non-obvious CloudFormation + Config behaviors (moved from SKILL.md)


- **Drift detection does NOT modify the stack.** `detect-stack-drift` is
  read-only. Remediation is a SEPARATE step (update-stack or change-set).

- **`detect-stack-drift` has an API rate limit.** Running detection on
  more than ~50 stacks simultaneously throttles. For fleets, stagger via
  SQS queue with batch size 10 or Step Functions map state.

- **Config's drift rule reads the LAST result.** It does NOT trigger new
  detection. If the last detection was 30 days ago, the rule reports
  30-day-old status. You MUST schedule periodic `detect-stack-drift`.

- **Not all resource types support drift detection.** Unsupported types
  report `NOT_CHECKED`. Common unsupported: `AWS::CloudFormation::Wait*`,
  nested stacks (now supported as of 2024-2025 — recurses into children).

- **Stack update reverts drift but may cause interruption.** For resources
  requiring replacement (immutable property changes), this means downtime.
  Always review the change-set before executing.

- **StackSet drift detection runs per stack-instance.** Iterate
  `list-stack-instances` and call `detect-stack-drift` per instance. For
  large StackSets (100+), use Step Functions Distributed Map.

- **Config Aggregator provides cross-account visibility WITHOUT deploying
  Lambda to each account.** The aggregator pulls Config data from members
  into a central account. Recommended pattern for multi-account.

- **Terraform `plan` detects drift against Terraform state, NOT CFN.** If
  resources are Terraform-managed, CFN drift detection does not apply.

## Step 10 — GitHub Actions drift-check workflow (moved from SKILL.md)


```yaml
name: Drift Detection
on:
  schedule: [{cron: '0 2 * * *'}]
jobs:
  drift-check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: hashicorp/setup-terraform@v3
      - run: |
          terraform init -input=false
          terraform plan -detailed-exitcode -out=plan.tfplan || exit_code=$?
          if [ $exit_code -eq 2 ]; then
            echo "::warning::Drift detected"
            terraform show -json plan.tfplan > drift.json
          fi
```

## Appendix A — Drift detection methods comparison (moved from SKILL.md)


| Method | Scope | Real-time? | Pros | Cons |
|---|---|---|---|---|
| `detect-stack-drift` (scheduled) | Per-stack | No (on-demand) | Comprehensive; all property diffs | Must schedule; rate limited |
| Config rule `cfn-stack-drift-check` | Per-stack | Near-real-time | Config compliance; Security Hub | Reads last result only |
| Custom Config rule (Lambda) | Per-resource | Real-time | Catches changes as they happen | No stack-level drift; custom Lambda |
| Terraform `plan -detailed-exitcode` | Per-state | Pipeline-driven | Native to Terraform; CI/CD | Terraform resources only |
| Config Aggregator | Cross-account | Near-real-time | Single pane across accounts | Read-only; no remediation |

## Appendix B — Drift remediation decision tree (moved from SKILL.md)


```
Is the stack production?
├─ Yes → Notify + human approval (aws:approve or Change Manager)
│        └─ Intentional hotfix? → update template
│           Unintentional?      → create change-set to revert
└─ No  → Remediation runbook tested?
        ├─ Yes → Auto-remediate via SSM (change-set re-apply)
        └─ No  → REVIEW_REQUIRED — test in sandbox first
```

## Recent AWS features (2024-2026) (moved from SKILL.md)


- **StackSets auto-deployment (2024):** New accounts in an OU
  automatically receive StackSet deployments, including the drift
  detection Lambda.

- **Nested stack drift detection (2024-2025):** `detect-stack-drift` now
  recurses into nested stacks. Previously showed as `NOT_CHECKED`.

- **Config Conformance Pack for drift (2024):** Managed pack
  `operational-best-practices-for-cloudformation` includes drift rules.

- **Change-set drift preview (2025):** `create-change-set` shows which
  drifted properties will be reverted, before execution.

- **Step Functions Distributed Map (2024):** Native iteration for > 10,000
  stack-instances with concurrency control. Replaces Lambda + SQS.

- **Config Aggregator advanced query (2025):** `select-aggregate-resource-
  config` SQL queries for cross-account drift without Athena.

## Expert heuristic: drift remediation blast radius (moved from SKILL.md)


Drift remediation on production stacks is the most dangerous governance
automation. Re-applying a template to "fix" drift can revert an
intentional hotfix, trigger resource replacement (downtime), or cascade
failures across dependent stacks.

> ALWAYS classify the stack (production vs non-production) before
> enabling auto-remediation. For production, require human approval.
> For non-production, validate the runbook in sandbox first.

**Stack classification techniques:**

| Technique | Mechanism | Limit |
|---|---|---|
| Stack name pattern | `prod-*` → approval | Name-based, fragile |
| Stack tags | `Environment: production` → manual | More robust; tag-driven |
| OU-based scoping | Prod OU → manual; Sandbox → auto | Strongest; org-level |
| Account isolation | Prod accounts excluded from auto | Complete isolation |
| Change Manager gate | All prod via Change Template | Human approval per execution |

**3-phase validation:**

1. **Sandbox — detect + auto-remediate:** Deploy full pipeline. Create
   deliberate drift. Verify detection → notification → remediation →
   `IN_SYNC`.
2. **Staging — detect + notify only:** Monitor drift patterns 1 week.
   Tune suppression rules for acceptable changes.
3. **Production — detect + notify only (permanent):** All remediation
   requires human-approved change-set. Never flip to auto without
   architecture review.

**Post-deploy alarms:** SSM Automation Executions Failed > 0 for the
remediation runbook. CFN drift status = DRIFTED for > 48 hours on
production stacks (detection fires but remediation never succeeds/approved).

**Surface in output:** `STACK_CLASS: <production | staging | dev |
sandbox>` and `REMEDIATION_MODE: <auto | approval-required | notify-only>`.
If `STACK_CLASS` is `production` and `REMEDIATION_MODE` is `auto`, flag
as UNSAFE.