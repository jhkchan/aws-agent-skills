# End-to-End Example: Cost Optimization Hub Optimization

A walkthrough showing how to use the
`cost-optimization-hub-optimizer` skill from invocation through
verification. Mirrors the structured-eval pattern of shipping
a concrete worked example per skill.

---

## Scenario

You are enabling Cost Optimization Hub across a multi-account
org and triaging the quick-win queue. The deployment needs:

- Organizations Payer: 123456789012 (management account)
- Member accounts: 14 linked
- Savings estimation mode: `AFTER_DISCOUNT`
- Look-back period: 14 days
- Compute Optimizer: already ACTIVE
- Quick-win threshold: Low effort, > $50/month in savings
- Tag: `Owner=finops`

---

## Step 1 — Invoke the skill

### Option A: Slash command

```
/aws:optimize-cost-optimization-hub
```

Then paste the requirements.

### Option B: Natural language

```
You: "Enable Cost Optimization Hub for the org payer
      123456789012 with all 14 member accounts. Use
      AFTER_DISCOUNT, 14-day look-back. Compute Optimizer
      is ACTIVE. List the Low-effort quick wins above
      $50/month."
```

### Option C: CLI routing

```bash
node cli/bin/cli.js route "enable cost optimization hub"
```

---

## Step 2 — Skill produces the FURTHER_OPTIMIZATION_AVAILABLE checklist

```text
COST_OPTIMIZATION_HUB: ACTIVE (Multi — Payer 123456789012, 14 members linked) — last refresh 2026-08-11T03:14Z
VERDICT: FURTHER_OPTIMIZATION_AVAILABLE
CHECKLIST:
  [✓] Enrollment status: ACTIVE
  [✓] Account scope: Multi (Payer 123456789012, 14 members linked)
  [✓] Compute Optimizer enrolled: ACTIVE
  [✓] Savings estimation mode: AFTER_DISCOUNT
  [✓] Look-back period: 14 days
  [✗] Total estimated savings: $4,820 / month ($57,840 annualized)
  [✗] Recommendation count: 87 (Applied: 12, Pending: 71, Ignored: 4)
  [✗] Quick-win queue (Low effort, savings > $50/mo): 23 recommendations, $1,910/mo ($22,920 annualized)
  [✓] Cost allocation tags: 3 active (Environment, Owner, CostCenter)
  [✓] CloudWatch alarms: 2 configured (NewRecommendations, SavingsRegression)
  [✓] Tags: Owner=finops, Cadence=weekly
VERIFICATION_COMMANDS:
  aws cost-optimization-hub get-enrollment-status
  aws cost-optimization-hub get-recommendation-summary
  aws cost-optimization-hub get-recommendations --filter '{"effort":"Low"}' --output table
  aws compute-optimizer get-enrollment-status
```

---

## Step 3 — Deployment commands

```bash
# Step 1: Enable the Hub on the Payer, with member accounts included
aws cost-optimization-hub update-enrollment-status \
  --status ACTIVE \
  --include-member-accounts

# Step 2: Configure preferences
aws cost-optimization-hub update-preferences \
  --savings-estimation-mode AFTER_DISCOUNT \
  --look-back-period-in-days 14

# Step 3: Verify Compute Optimizer is ACTIVE (gates right-size recs)
aws compute-optimizer get-enrollment-status
# Expected: ACTIVE

# Step 4: Pull the Low-effort quick-win queue
aws cost-optimization-hub get-recommendations \
  --filter '{"effort":"Low"}' \
  --query 'items[*].{Resource:resourceArn,Savings:estimatedMonthlySavings,Action:action}' \
  --output table

# Step 5: Apply the top quick-wins (example: release unattached EIPs)
for EIP in eipalloc-aaa eipalloc-bbb eipalloc-ccc; do
  aws ec2 release-address --allocation-id "$EIP"
done

# Step 6: Mark the recommendations APPLIED
aws cost-optimization-hub batch-update-recommendation-status \
  --request '{"recommendationIds":["rec-aaa","rec-bbb","rec-ccc"],"status":"APPLIED"}'

# Step 7: Set up the CloudWatch alarm for new recommendations
aws cloudwatch put-metric-alarm \
  --alarm-name "CostOptHub-New-Recommendations" \
  --namespace CostOptimizationHub \
  --metric-name RecommendationCount \
  --statistic Maximum --period 86400 \
  --threshold 1 --comparison-operator GreaterThanThreshold \
  --evaluation-periods 1 \
  --alarm-actions "arn:aws:sns:us-east-1:123456789012:finops-alerts"
```

---

## Step 4 — Post-deployment verification

```bash
# Enrollment status
aws cost-optimization-hub get-enrollment-status
# Expected: ACTIVE

# Multi-account scope
aws cost-optimization-hub get-enrollment-statuses \
  --query 'items[?status==`ACTIVE`] | length(@)'
# Expected: 15 (payer + 14 members)

# Compute Optimizer still ACTIVE
aws compute-optimizer get-enrollment-status

# Recommendation summary
aws cost-optimization-hub get-recommendation-summary
# Verify lastRefresh is within 24h

# Quick-win queue size after applying the batch
aws cost-optimization-hub get-recommendations \
  --filter '{"effort":"Low","implementationStatus":"PENDING"}' \
  --query 'items | length(@)'
# Expected: fewer than before

# CloudWatch alarm created
aws cloudwatch describe-alarms \
  --alarm-names "CostOptHub-New-Recommendations" \
  --query 'MetricAlarms[*].StateValue' --output text
# Expected: OK or INSUFFICIENT_DATA on day 1
```

---

## What the skill catches that a naive deployment misses

| Configuration | Naive deployment | Skill output | Why the skill is right |
|---|---|---|---|
| Multi-account scope | Forgets `--include-member-accounts` | Payer-anchored multi-account with verification | Without the flag, member accounts are invisible to the Hub |
| Compute Optimizer | Assumes right-size will appear | Verifies CO enrollment before claiming coverage | The Hub's right-size recommendations are EMPTY without CO |
| Savings mode | Default to BEFORE_DISCOUNT | AFTER_DISCOUNT for RI/SP holders | BEFORE_DISCOUNT overstates savings when RIs/SPs apply |
| Annualization | Quotes monthly as annual | Labels period explicitly | Mislabeling inflates/deflates the number 12× |
| Effort prioritization | Sorts by savings only | Filters Low-effort first | Quick wins deliver 60-80% of savings at <30% of effort |
| Status tracking | Marks APPLIED and assumes savings | Verifies via Cost Explorer next cycle | APPLIED is operator assertion; verify realization |
| CloudWatch namespace | Creates alarm before enrollment | Confirms ACTIVE first | Namespace publishes only when ACTIVE |
| Cost allocation tags | Expects tag filter to just work | Verifies activation in Cost Explorer | User-defined tags need explicit activation |

---

## Related artifacts

- **Skill definition:** `skills/cost-optimization-hub-optimizer/SKILL.md`
- **Savings and effort guide:** `skills/cost-optimization-hub-optimizer/references/savings-and-effort.md`
- **Multi-account and alerts guide:** `skills/cost-optimization-hub-optimizer/references/multi-account-and-alerts.md`
- **Slash command:** `commands/aws/optimize-cost-optimization-hub.md`
- **Eval suite:** `skills/cost-optimization-hub-optimizer/evals/evals.json`
- **Legacy test cases:** `skills/cost-optimization-hub-optimizer/eval/test-cases.yaml`
