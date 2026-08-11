# End-to-end usage scenario: cloudwatch-synthetics-troubleshooter

A walkthrough showing the skill diagnosing a CloudWatch Synthetics
canary failure caused by a Visual Monitoring baseline mismatch after a
UI deployment. This exercises Step 1 (symptom identification), Step 4
(Visual Monitoring), the post-deploy baseline distinction, and the
remediation workflow.

## Input (user prompt)

> Our `checkout-ui-canary` in `us-east-1` just started failing. It's a
> GUI Selenium canary. The run report shows
> `VisualMonitoringBaselineMismatch` on step 3 (payment-page) with a
> 12.4% pixel delta. `SuccessPercent` dropped to 0% at 14:02Z. Duration
> is 18s (normal). We deployed a checkout redesign at 14:00Z — the "Pay
> Now" button moved and a trust badge was added. The tolerance is 1%.

## Skill output

```text
CANARY: checkout-ui-canary in us-east-1
VERDICT: ROOT_CAUSE_FOUND
ROOT_CAUSE: VISUAL_MONITORING_MISMATCH — the checkout page was
  redesigned and deployed at 2026-08-09T14:00Z. The Visual Monitoring
  baseline was not updated. Step 3 (payment page) shows a 12.4% pixel
  delta vs the 1% tolerance: "Pay Now" button moved from right-aligned
  to center, and a new trust badge appears below the total.
FAILURE_TYPE: VISUAL_MONITORING_MISMATCH
EVIDENCE:
  - Run report: VisualMonitoringBaselineMismatch on step 3, delta 12.4%
  - CloudWatch SuccessPercent: dropped 100% to 0% at 2026-08-09T14:02Z
  - CloudWatch Duration: 18s (normal) — canary functionally succeeded
  - Deployment correlation: checkout-ui deployed at 2026-08-09T14:00Z
ROOT_CAUSE_CATALOG: #4
REMEDIATION:
  1. Confirm the UI change is intentional with the frontend team.
  2. Update the Visual Monitoring baseline via console or trigger:
      aws synthetics start-canary --name checkout-ui-canary
     Then update baseline from the new run's screenshots.
  3. Optionally increase tolerance to 2% for minor CSS shifts.
  4. Monitor SuccessPercent for 10 minutes; expect return to 100%.
```

## What the skill caught that a generic assistant misses

1. **Post-deploy vs production incident.** A generic assistant treats
   the failure as a production incident. The skill recognises that a
   post-deploy Visual Monitoring mismatch is EXPECTED — the baseline is
   stale, not the application broken.

2. **Functional success vs visual failure.** A generic assistant may
   not distinguish between the canary functionally failing (clicks,
   navigation) and the visual comparison failing. The skill notes that
   Duration is normal (18s) and all steps functionally completed — only
   the screenshot comparison flagged the delta.

3. **Deployment correlation.** The skill correlates the failure start
   time (14:02Z) with the deployment time (14:00Z) as primary evidence
   that the UI change is the root cause of the baseline mismatch.

4. **Specific remediation.** A generic assistant recommends "fix it" or
   "increase tolerance." The skill specifies updating the baseline as
   the correct action, with the CLI command and the post-apply
   monitoring step.

## Slash-command invocation

```
/aws:troubleshoot-cloudwatch-synthetics
```

Or via the orchestrator:

```
/aws:pipeline
You: "checkout-ui-canary is failing with VisualMonitoringBaselineMismatch after our UI deploy"
```

The orchestrator emits `[Phase: Troubleshoot | Skills routed:
cloudwatch-synthetics-troubleshooter]` and hands off to this skill for
the VERDICT.

## Live-account diagnostic flow (requires AWS CLI)

```bash
# Get the canary configuration including Visual Monitoring tolerance.
aws synthetics describe-canary --name checkout-ui-canary \
  --query 'Canary.{type:Type,runtime:RuntimeVersion,timeout:RunConfig.TimeoutInSeconds,visual:RunConfig}'

# Get the failed run report.
aws synthetics get-canary-runs --name checkout-ui-canary --max-results 3 \
  --query 'CanaryRuns[*].{status:Status,state:State,duration:Timing.Duration}'

# Download the step screenshots for comparison.
aws s3 ls s3://cw-synthetics-artifacts-prod/canary/checkout-ui-canary/ --recursive --human-readable

# Check SuccessPercent trend.
aws cloudwatch get-metric-statistics --namespace CloudWatchSynthetics \
  --metric-name SuccessPercent --dimensions Name=CanaryName,Value=checkout-ui-canary \
  --start-time $(date -u -v-1H +%Y-%m-%dT%H:%M:%SZ) --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
  --period 300 --statistics Average --output json
```

If the run report shows `VisualMonitoringBaselineMismatch` and the
failure correlates with a confirmed UI deployment, the diagnosis is
confirmed as VISUAL_MONITORING_MISMATCH with a stale baseline. The fix
is to update the baseline, not to revert the deployment.
