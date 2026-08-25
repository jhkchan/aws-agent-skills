# Diagnostic Commands — Well-Architected Review Operator

Load-on-demand command listings moved verbatim from SKILL.md: pre-flight metadata gate, PDF report variant, milestone listing, Trusted Advisor integration and pulling, completeness verification, and tag/share close-out.

## Pre-flight: workload / lens metadata gate
Run before classification. `list-workloads` returns max 50/page
(`--max-results 50`, paginate with `--next-token`).

**Live-account pre-flight (skip if offline plan):**
1. `aws wellarchitected list-workloads` — confirm workload
   exists; capture `WorkloadId`, `WorkloadArn`, `Environment`.
2. `aws wellarchitected list-lenses --workload-id <id>` —
   confirm lens is associated with the workload.
3. `aws wellarchitected get-workload --workload-id <id>` —
   read `Lenses[]`, `PillarIds[]`, `ReviewOwner`,
   `IsReviewOwnerUpdateAllowed`.
4. `aws wellarchitected list-answers --workload-id <id>
   --lens-alias wellarchitected` — check current answer state
   for the target pillar.
5. `aws wellarchitected list-share-invitations` — confirm
   cross-account sharing state if applicable.
6. `aws trustedadvisor describe-checks --region <r>` — confirm
   TA checks available for the pillar integration.
7. `aws sts get-caller-identity` — confirm caller identity and
   IAM permissions.

**Malformed input:** emit `VERDICT: ERROR` with reason and
remediation.

## Step 4 — consolidated report PDF variant
For a PDF report, use `--format PDF`:

```bash
aws wellarchitected get-consolidated-report \
  --workload-id <id> \
  --format PDF \
  --region us-east-1 > /tmp/war-report.pdf
```

## Step 6 — list milestones
```bash
aws wellarchitected list-milestones \
  --workload-id <id> \
  --region us-east-1
```

## Step 7 — Trusted Advisor findings integration
Trusted Advisor findings map to specific Well-Architected
questions. The integration pre-populates evidence but does
NOT auto-answer — the operator must confirm the answer.

```bash
aws trustedadvisor describe-checks --region us-east-1
aws trustedadvisor describe-check-refresh-statuses --region us-east-1
aws trustedadvisor get-check-result \
  --check-id <check-id> \
  --region us-east-1
```

Map TA findings to Well-Architected questions:
- **Cost Optimization checks** (e.g., `LowUtilizationEC2Resources`)
  → Cost Optimization pillar questions on right-sizing.
- **Security checks** (e.g., `IAMPasswordPolicy`) → Security
  pillar questions on IAM hygiene.
- **Performance checks** (e.g., `HighUtilizationEC2Instance`)
  → Performance pillar questions on capacity planning.
- **Fault Tolerance checks** (e.g., `MultiAZEC2`) →
  Reliability pillar questions on multi-AZ deployment.

The skill surfaces the TA evidence in the answer rationale,
then prompts the operator to confirm the risk-tier selection.

## Step 9 — verify review completeness
After answering all pillar questions, verify the review is
complete:

```bash
aws wellarchitected list-answers \
  --workload-id <id> \
  --lens-alias wellarchitected \
  --pillar-id operationalExcellence \
  --region us-east-1 | jq '.AnswerSummaries | length'

# Repeat for each pillar: security, reliability, performance,
# costOptimization, sustainability
```

A pillar is complete when every question has at least one
selected choice. Unanswered questions appear as `UNANSWERED`
in the consolidated report.

## Step 10 — tag, share, and close
Tag the workload for governance tracking; optionally share
cross-account:

```bash
aws wellarchitected tag-resource \
  --workload-arn arn:aws:wellarchitected:us-east-1:111122223333:workload/<id> \
  --tags team=payments,env=prod,review-cycle=2026-Q3

# Cross-account share (recipient account must accept)
aws wellarchitected create-workload-share \
  --workload-id <id> \
  --shared-with 111122223334 \
  --permission-mode REVIEWER \
  --region us-east-1
```

## Trusted Advisor integration
Trusted Advisor (TA) is the operational signal source for
Well-Architected reviews. The integration is read-only — TA
findings inform the answer rationale but the operator must
confirm the risk-tier selection.

### TA check categories

| Category | Maps to pillar | Example check |
|---|---|---|
| Cost Optimization | `costOptimization` | LowUtilizationEC2Resources |
| Security | `security` | IAMPasswordPolicy, RootAccountMFA |
| Performance | `performance` | HighUtilizationEC2Instance |
| Fault Tolerance | `reliability` | MultiAZEC2, ELBConnectionDraining |
| Service Limits | `operationalExcellence` | ServiceLimits

### Pulling TA findings

```bash
# List all checks
aws trustedadvisor describe-checks --region us-east-1

# Get a check result
aws trustedadvisor get-check-result \
  --check-id <check-id> \
  --region us-east-1
```

The skill maps each TA finding to the corresponding
Well-Architected question, surfaces the evidence in the answer
rationale, and prompts the operator to confirm the risk-tier.
