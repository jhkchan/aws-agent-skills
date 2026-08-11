# Review CLI commands — deep reference

This reference expands the SKILL.md review procedure with the
full copy-pasteable CLI command sequence for all 10 review
steps, per-pillar answer patterns, lens import, TA integration,
milestone lifecycle, and cross-account sharing. Load when
conducting a full review lifecycle.

## Workload lifecycle

### Create

```bash
aws wellarchitected create-workload \
  --workload-name "checkout-service" \
  --description "Checkout microservice handling payment authorization and order capture" \
  --environment PRODUCTION \
  --review-owner "payments-platform@example.com" \
  --lenses wellarchitected wellarchitected-prosperity \
  --aws-regions us-east-1 us-west-2 \
  --account-ids 111122223333 \
  --pillar-ids "operationalExcellence" "security" "reliability" \
    "performance" "costOptimization" "sustainability" \
  --notes "Quarterly review 2026-Q3" \
  --region us-east-1
```

Capture `WorkloadId` from the response.

### Read

```bash
aws wellarchitected get-workload --workload-id <id> --region us-east-1
aws wellarchitected list-workloads --region us-east-1
```

### Update

```bash
aws wellarchitected update-workload \
  --workload-id <id> \
  --workload-name "checkout-service-v2" \
  --description "Updated description" \
  --review-owner "new-owner@example.com" \
  --environment PRODUCTION \
  --region us-east-1
```

### Delete

```bash
aws wellarchitected delete-workload --workload-id <id> --region us-east-1
```

## Lens lifecycle

### Import a specialty lens into the account

```bash
aws wellarchitected import-lens \
  --lens-alias wellarchitected-prosperity \
  --region us-east-1
```

Specialty lenses: `wellarchitected-saas`, `wellarchitected-ftr`,
`wellarchitected-healthcare`, `wellarchitected-prosperity`,
`wellarchitected-financial-services`, plus any custom lenses
published by the account.

### Associate a lens with a workload

```bash
aws wellarchitected associate-lenses \
  --workload-id <id> \
  --lens-aliases wellarchitected-prosperity \
  --region us-east-1
```

### Disassociate

```bash
aws wellarchitected disassociate-lenses \
  --workload-id <id> \
  --lens-aliases wellarchitected-prosperity \
  --region us-east-1
```

### List lenses

```bash
# All lenses available in the account
aws wellarchitected list-lenses --region us-east-1

# Lenses associated with a workload
aws wellarchitected list-lenses --workload-id <id> --region us-east-1
```

## Answer pillar questions

### Per-pillar answer pattern

For each pillar, enumerate the canonical question set and emit
`update-answer` with the `ChoiceUpdates` map:

```bash
aws wellarchitected update-answer \
  --workload-id <id> \
  --lens-alias wellarchitected \
  --question-id <question-id> \
  --choice-updates '{
    "<safe-choice-id>": {
      "Status": "SELECTED",
      "Reason": "OUT_OF_SCOPE",
      "Notes": "Choice not applicable — workload is serverless"
    },
    "<risky-choice-id>": {
      "Status": "NOT_SELECTED",
      "Reason": "RISK_GUIDANCE",
      "Notes": "No automated rollback — HIGH risk per APP-SVC rollback SOP"
    }
  }' \
  --notes "Answered by review-operator skill" \
  --region us-east-1
```

### Discover question IDs

```bash
aws wellarchitected list-answers \
  --workload-id <id> \
  --lens-alias wellarchitected \
  --pillar-id security \
  --region us-east-1

# Or list questions per pillar via the lens:
aws wellarchitected get-lens \
  --lens-alias wellarchitected \
  --lens-version <version> \
  --region us-east-1
```

### Get a single answer

```bash
aws wellarchitected get-answer \
  --workload-id <id> \
  --lens-alias wellarchitected \
  --question-id <question-id> \
  --region us-east-1
```

### Risk-tier semantics

| Reason code | Meaning | Effect on improvement plan |
|---|---|---|
| `RISK_GUIDANCE` | Choice introduces risk; default to HIGH or MEDIUM | Item added |
| `OUT_OF_SCOPE` | Choice not applicable to the workload | No item |
| `ARCHITECTURE_DECISION` | Deliberate design trade-off accepted | Documented but no action |

## Consolidated report

### JSON format

```bash
aws wellarchitected get-consolidated-report \
  --workload-id <id> \
  --format JSON \
  --include-shared-resources \
  --region us-east-1 > /tmp/war-report-$(date +%s).json
```

### PDF format

```bash
aws wellarchitected get-consolidated-report \
  --workload-id <id> \
  --format PDF \
  --region us-east-1 > /tmp/war-report-$(date +%s).pdf
```

The PDF report includes per-pillar risk distribution charts,
lens-specific findings, workload metadata, and the review owner.

## Improvement plan

### List improvement plan items

```bash
aws wellarchitected list-answers \
  --workload-id <id> \
  --lens-alias wellarchitected \
  --region us-east-1 | jq '.AnswerSummaries[] | select(.ChoiceAnswerSummaries[]?.Reason=="RISK_GUIDANCE")'
```

The consolidated report enumerates every `HIGH_ISSUE` and
`MEDIUM_ISSUE` answer with the underlying question, the risky
choice, and the AWS-provided guidance text.

### Per-pillar filtering

```bash
aws wellarchitected list-answers \
  --workload-id <id> \
  --lens-alias wellarchitected \
  --pillar-id security \
  --region us-east-1 | jq '.AnswerSummaries | length'
```

## Milestone lifecycle

### Create

```bash
aws wellarchitected create-milestone \
  --workload-id <id> \
  --milestone-name "2026-Q3-baseline" \
  --region us-east-1
```

Capture `MilestoneNumber` from the response. The milestone
captures the current answer set and improvement plan at the
moment of creation — subsequent answer updates do NOT
back-propagate.

### List milestones

```bash
aws wellarchitected list-milestones \
  --workload-id <id> \
  --region us-east-1
```

### Get a milestone snapshot

```bash
aws wellarchitected get-milestone \
  --workload-id <id> \
  --milestone-number <num> \
  --region us-east-1
```

## Trusted Advisor integration

### List available checks

```bash
aws trustedadvisor describe-checks --region us-east-1
```

### Get check result

```bash
aws trustedadvisor get-check-result \
  --check-id LowUtilizationEC2Resources \
  --region us-east-1
```

### Refresh a check

```bash
aws trustedadvisor refresh-check \
  --check-id LowUtilizationEC2Resources \
  --region us-east-1
```

### TA check to pillar mapping

| TA check | Category | Maps to pillar |
|---|---|---|
| `LowUtilizationEC2Resources` | cost | costOptimization |
| `IdleDBInstances` | cost | costOptimization |
| `UnassociatedElasticIPAddresses` | cost | costOptimization |
| `IAMPasswordPolicy` | security | security |
| `RootAccountMFA` | security | security |
| `IamUserUnusedCredentials` | security | security |
| `HighUtilizationEC2Instance` | performance | performance |
| `ServiceLimits` | fault_tolerance | operationalExcellence, reliability |
| `MultiAZEC2` | fault_tolerance | reliability |
| `ELBConnectionDraining` | fault_tolerance | reliability |
| `ELBCrossZoneLoadBalancing` | fault_tolerance | reliability |

### Pattern: surface TA in answer rationale

```bash
TA_RESULT=$(aws trustedadvisor get-check-result \
  --check-id LowUtilizationEC2Resources \
  --region us-east-1 \
  --query 'result.flaggedResources' --output json)

COUNT=$(echo $TA_RESULT | jq 'length')

aws wellarchitected update-answer \
  --workload-id <id> \
  --lens-alias wellarchitected \
  --question-id <right-sizing-question-id> \
  --choice-updates '{
    "<gap-choice-id>": {
      "Status": "NOT_SELECTED",
      "Reason": "RISK_GUIDANCE",
      "Notes": "TA LowUtilizationEC2Resources reports '"$COUNT"' underutilized instances — operator-confirmed risk tier"
    }
  }' \
  --region us-east-1
```

## Cross-account sharing

### Create a share

```bash
aws wellarchitected create-workload-share \
  --workload-id <id> \
  --shared-with 111122223334 \
  --permission-mode REVIEWER \
  --region us-east-1
```

`permission-mode` options:
- `READ_ONLY` — recipient can view answers and reports.
- `REVIEWER` — recipient can update answers.
- `CONTRIBUTOR` — recipient can modify workload metadata.

### Accept a share (in the recipient account)

```bash
aws wellarchitected accept-workload-share \
  --share-id <share-id> \
  --region us-east-1
```

### List shares

```bash
aws wellarchitected list-share-invitations --region us-east-1
aws wellarchitected list-workload-shares --workload-id <id> --region us-east-1
```

## Terraform equivalents

```hcl
resource "aws_wellarchitected_workload" "checkout" {
  name             = "checkout-service"
  description      = "Checkout microservice"
  environment      = "PRODUCTION"
  review_owner     = "payments-platform@example.com"
  aws_regions      = ["us-east-1", "us-west-2"]
  account_ids      = ["111122223333"]
  lenses           = ["wellarchitected", "wellarchitected-prosperity"]
  pillar_priorities = [
    "operationalExcellence",
    "security",
    "reliability",
    "performance",
    "costOptimization",
    "sustainability"
  ]
}

resource "aws_wellarchitected_workload_share" "cross_account" {
  workload_id    = aws_wellarchitected_workload.checkout.id
  shared_with    = "111122223334"
  permission_mode = "REVIEWER"
}

resource "aws_wellarchitected_milestone" "baseline" {
  workload_id    = aws_wellarchitected_workload.checkout.id
  milestone_name = "2026-Q3-baseline"
}
```

## Verification suite (run after a full review)

```bash
# Workload exists
aws wellarchitected get-workload --workload-id <id> --region us-east-1

# Lenses associated
aws wellarchitected list-lenses --workload-id <id> --region us-east-1

# Answer coverage per pillar
for PILLAR in operationalExcellence security reliability performance costOptimization sustainability; do
  echo "=== $PILLAR ==="
  aws wellarchitected list-answers \
    --workload-id <id> \
    --lens-alias wellarchitected \
    --pillar-id $PILLAR \
    --region us-east-1 | jq '.AnswerSummaries | length'
done

# Improvement plan items
aws wellarchitected list-answers \
  --workload-id <id> \
  --lens-alias wellarchitected \
  --region us-east-1 | jq '[.AnswerSummaries[] | select(.ChoiceAnswerSummaries[]?.Reason=="RISK_GUIDANCE")] | length'

# Milestone list
aws wellarchitected list-milestones --workload-id <id> --region us-east-1

# Consolidated report (JSON)
aws wellarchitected get-consolidated-report --workload-id <id> --format JSON --region us-east-1

# Tag verification
aws wellarchitected list-tags-for-resource \
  --workload-arn arn:aws:wellarchitected:us-east-1:111122223333:workload/<id>
```

## Common pitfalls (extended)

### Choice ID mismatch

The `ChoiceUpdates` map keys must match the choice IDs defined
in the lens. A wrong choice ID silently fails to persist the
answer. Verify the choice ID via `get-lens` before
`update-answer`.

### Lens not associated

`update-answer` against a lens not associated with the workload
returns `ResourceNotFoundException`. Run `associate-lenses`
first.

### Milestone captured wrong state

A milestone is a point-in-time snapshot. If answers changed
after the milestone, create a new milestone. Milestones cannot
be updated.

### Cross-account share not accepted

The recipient account must accept the share via
`accept-workload-share`. The workload does NOT appear in the
recipient account until accepted.

### Prosperity lens missing

The Prosperity lens (`wellarchitected-prosperity`) is a
specialty lens delivered separately from the base Framework.
Run `import-lens` then `associate-lenses` before answering
Prosperity questions.
