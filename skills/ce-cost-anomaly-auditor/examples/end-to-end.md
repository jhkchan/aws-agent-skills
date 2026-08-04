# End-to-end usage scenario: ce-cost-anomaly-auditor

A walkthrough showing the skill auditing a Cost Explorer configuration
that has an IMMEDIATE monitor paired with a WEEKLY subscription
(CONFIG_GAP — frequency mismatch), a $100 default threshold on a $20k/mo
account (CONFIG_GAP — threshold miscalibrated), and low RI/SP coverage
(LOW_RI_COVERAGE), demonstrating verdict aggregation, the
frequency-vs-detection-cadence distinction, and the coverage-vs-
utilization distinction.

## Input (user prompt)

> Review our Cost Explorer and Cost Anomaly Detection setup before the
> quarterly billing review. We spend about $20k/month on steady-state EC2
> and want to make sure we're not leaking on-demand spend or missing cost
> spikes.

```yaml
Account id: 111111111111
Cost Explorer: enabled
Account spend profile: $20,000/month (steady-state EC2)
Cost Anomaly Detection monitors:
  - MonitorArn: arn:aws:ce::111111111111:anomalyMonitor/imm-prod
    MonitorName: imm-prod
    MonitorType: IMMEDIATE
Cost Anomaly Detection subscriptions:
  - SubscriptionArn: arn:aws:ce::111111111111:anomalySubscription/weekly-digest
    SubscriptionName: weekly-digest
    Threshold: 100.0
    Frequency: WEEKLY
    MonitorArn: arn:aws:ce::111111111111:anomalyMonitor/imm-prod
    Subscribers: [{Address: finops@corp.com, Type: EMAIL}]
RI coverage (7-day avg): 22% (over $18,000 eligible EC2 spend)
SP coverage (7-day avg): 12% (over $18,000 eligible EC2 spend)
CUR v2 with IncludeResourceIDs: enabled (Athena-integrated)
Free-tier: no
```

## Skill output

```text
ACCOUNT: 111111111111
VERDICT: LOW_RI_COVERAGE
REASON: Account runs $18k/mo eligible EC2 spend with 22% RI / 12% SP coverage
(Step 2) — significant on-demand leak on a steady-state fleet where a
commitment would offset material spend. Additionally, the IMMEDIATE monitor
is paired with a WEEKLY subscription (Step 3a — notification latency 7x
detection latency) and the $100 threshold is miscalibrated for a $20k/mo
account (Step 3b — recommended $1000-$2000).
FINDINGS:
  - [MEDIUM] LOW_RI_COVERAGE: 22% RI / 12% SP coverage on $18k/mo eligible
    compute (Step 2) — commitment strategy absent or undersized
  - [MEDIUM] FREQUENCY_MISMATCH: IMMEDIATE monitor arn:aws:ce::111111111111:
    anomalyMonitor/imm-prod linked to WEEKLY subscription — detects in ~5 min,
    reports in 7 days (Step 3a)
  - [MEDIUM] THRESHOLD_MISALIGNED: $100 threshold on $20k/mo spend —
    recommended ~$1000-$2000 (5-10% of monthly) (Step 3b)
  - [OK] CUR v2 with IncludeResourceIDs configured — idle detection ready
REMEDIATION:
  1. MEDIUM — Run a commitment analysis to size the RI/SP gap:
     aws ce get-reservation-utilization --region us-east-1 --profile <p>
       --time-period Start=2026-07-21,End=2026-07-28 --granularity DAILY
     aws ce get-savings-plans-utilization --region us-east-1 --profile <p>
       --time-period Start=2026-07-21,End=2026-07-28 --granularity DAILY
     Target 70-90% coverage on the steady-state EC2/Fargate base. Prefer
     Compute Savings Plans for flexibility on workloads with instance churn.
  2. MEDIUM — Update the subscription frequency to IMMEDIATE:
     aws ce update-anomaly-subscription --region us-east-1 --profile <p>
       --subscription-arn arn:aws:ce::111111111111:anomalySubscription/weekly-digest
       --frequency IMMEDIATE
  3. MEDIUM — Update the threshold to ~$1000 (5% of monthly spend):
     aws ce update-anomaly-subscription --region us-east-1 --profile <p>
       --subscription-arn arn:aws:ce::111111111111:anomalySubscription/weekly-digest
       --threshold 1000
```

## What the skill caught that a generic assistant misses

1. **The Frequency-vs-detection-cadence distinction.** A generic assistant
   says "consider changing the subscription frequency." The skill explains
   that the IMMEDIATE monitor detects anomalies in ~5 minutes on new line
   items, but the WEEKLY subscription delivers a digest 7 days later — the
   operator sees the spike a week late. The monitor is working; the
   subscription is the bottleneck. This is CONFIG_GAP, not OK.

2. **Coverage-vs-utilization distinction.** A generic assistant says "buy
   more RIs." The skill distinguishes: this skill audits COVERAGE (how
   much usage was commitment-offset — the on-demand leak), NOT
   utilization (how much commitment was consumed — over-buy waste). The
   LOW_RI_COVERAGE verdict means "run a commitment analysis," not "buy RIs
   today" — the commitment decision needs utilization context first.

3. **Threshold calibration to spend.** A generic assistant notes "$100 is
   the default." The skill explains that on a $20k/mo account, $100
   generates noise on normal fluctuation (too low), while on a free-tier
   account it would be too high. The calibration is 5-10% of monthly spend
   — for this account, $1000-$2000.

4. **Severity aggregation with per-finding breakdown.** The verdict is
   LOW_RI_COVERAGE (the worst finding), but the FINDINGS list shows the
   individual severities: the coverage gap is MEDIUM, the frequency
   mismatch is MEDIUM, the threshold is MEDIUM, and CUR is OK. This lets
   the operator triage each finding independently.

## Slash-command invocation

```
/aws:audit-ce-cost-anomaly
```

Or via the orchestrator:

```
/aws:pipeline
You: "audit our Cost Explorer setup before the billing review"
```

The orchestrator emits
`[Phase: Audit | Skills routed: ce-cost-anomaly-auditor]` and hands off
to this skill for the VERDICT.

## CLI routing

```bash
node cli/bin/cli.js route "audit cost anomaly detection"
# [Phase: Audit | Skills routed: ce-cost-anomaly-auditor]
```

## Live-account follow-up (optional, requires AWS CLI)

After remediating the subscription, validate the CAD posture:

```bash
# Verify the subscription frequency and threshold are updated
aws ce get-anomaly-subscriptions --region us-east-1 --profile default \
  --monitor-arn arn:aws:ce::111111111111:anomalyMonitor/imm-prod

# Check RI/SP coverage after commitment purchase (7-day trailing window)
aws ce get-reservation-coverage --region us-east-1 --profile default \
  --time-period Start=2026-07-21,End=2026-07-28 --granularity DAILY \
  --metrics Coverage

aws ce get-savings-plans-coverage --region us-east-1 --profile default \
  --time-period Start=2026-07-21,End=2026-07-28 --granularity DAILY \
  --metrics Coverage
```

Then monitor the anomaly subscription for IMMEDIATE delivery on the next
spike for 1-2 weeks to confirm the frequency fix took effect.
