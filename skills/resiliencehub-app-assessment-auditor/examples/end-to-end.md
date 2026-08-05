# End-to-end usage scenario: resiliencehub-app-assessment-auditor

A walkthrough showing the skill auditing a Resilience Hub application
whose latest assessment is 95 days old (STALE_ASSESSMENT), demonstrating
the staleness-first precedence, the per-tier compliance analysis, and the
re-assessment remediation workflow.

## Input (user prompt)

> Audit this Resilience Hub app assessment before our upcoming production
> launch. I need to know if our resiliency posture is ready.

```
Today's date: 2026-08-05

App ARN: arn:aws:resiliencehub:us-east-1:111111111111:app/payment-platform
App name: payment-platform
Current app version: 4
App policyArn (attached): arn:aws:resiliencehub:us-east-1:111111111111:resiliency-policy/prod-mc

Latest assessment:
  assessmentArn: arn:aws:resiliencehub:us-east-1:111111111111:app-assessment/asmt-991
  assessmentStatus: Success
  appVersion: 3
  startTime: 2026-05-01T08:00:00Z
  endTime: 2026-05-02T10:00:00Z
  complianceScore: 92
  driftStatus: NotChecked

Resiliency policy (prod-mc):
  MissionCritical: {RTO: 5 min, RPO: 5 min}
  Critical: {RTO: 1 hr, RPO: 15 min}
  Standard: {RTO: 24 hr, RPO: 24 hr}

Compliance map:
  checkout-api:     tier=MissionCritical, complianceStatus=PolicyCompliant
  fraud-engine:     tier=MissionCritical, complianceStatus=PolicyCompliant
  payment-db-proxy: tier=Critical,         complianceStatus=PolicyCompliant
  settlement-svc:   tier=Critical,         complianceStatus=PolicyNotCompliant
  email-notifier:   tier=Standard,         complianceStatus=PolicyCompliant
  report-job:       tier=Standard,         complianceStatus=PolicyCompliant

Recommendations:
  Alarm: 5 total, 2 implemented
  SDD:   2 total, 1 implemented
  Test:  1 total, 0 implemented
```

## Skill output

```text
APP: arn:aws:resiliencehub:us-east-1:111111111111:app/payment-platform
VERDICT: STALE_ASSESSMENT
REASON: The latest successful assessment ended on 2026-05-02 — 95 days ago
(Step 2). Despite a complianceScore of 92, the assessment predates appVersion
4 (assessment references version 3), meaning the compliance data does not
reflect the current published app. Staleness takes precedence over all
downstream findings — the 92 is a historical score, not a current posture.
FINDINGS:
  - [STALE_ASSESSMENT] Assessment endTime 2026-05-02 is 95 days old (> 90
    day threshold, Step 2) — compliance data is unreliable
  - [CONFIG_GAP] Assessment references appVersion 3 but current app version
    is 4 (Step 3) — resources added/removed in version 4 are not covered
  - [CONFIG_GAP] 3 of 5 CloudWatch alarm recommendations are not implemented
    (Step 7) — unimplemented alarms are an operational detection gap
  - [OK] Resiliency policy is attached with valid tier-to-RTO/RPO mapping
    (Step 4)
  - [Note] settlement-svc (Critical tier) is PolicyNotCompliant — this
    finding is from the stale assessment and must be re-verified after a
    fresh assessment runs
REMEDIATION:
  1. Publish the current draft (if any) and re-run the assessment:
     aws resiliencehub publish-app-version --app-arn <arn> --profile <p>
     aws resiliencehub start-app-assessment \
       --app-arn <arn> --app-version 4 \
       --assessment-name pre-launch-$(date +%Y%m%d) \
       --policy-arn arn:aws:resiliencehub:us-east-1:111111111111:resiliency-policy/prod-mc \
       --profile <p>
  2. After the new assessment completes (Success), re-audit to get a
     fresh verdict. The Critical-tier NonCompliant on settlement-svc must
     be re-verified — if it persists, the verdict will escalate to HIGH_RISK.
  3. Implement the 3 pending alarm recommendations before the launch:
     aws resiliencehub get-recommendation-template --template-arn <arn>
     then deploy the CloudWatch composite alarms via CloudFormation.
```

## What the skill caught that a generic assistant misses

1. **Staleness overrides a good score.** A generic assistant sees
   complianceScore 92 and says "looks healthy." The skill computes the
   assessment age (95 days > 90-day threshold) and emits STALE_ASSESSMENT
   — the 92 is three months old and references an older app version. This
   is the most common Resilience Hub audit error: trusting a stale score.

2. **appVersion drift is detected.** The assessment references appVersion
   3, but the current app version is 4. Resources added in version 4 are
   not covered by this assessment. A generic assistant does not cross-
   reference the assessment's appVersion against the current app version.

3. **The Critical-tier NonCompliant is contextualised, not verdict-
   driving.** settlement-svc (Critical tier) is PolicyNotCompliant, which
   would normally trigger HIGH_RISK (Step 5a). But because the assessment
   is stale, the finding is retained as context ("must be re-verified")
   rather than driving the verdict. The staleness finding takes
   precedence — reporting HIGH_RISK on a stale assessment gives false
   precision.

4. **Alarm gaps are distinguished from Test gaps.** 3 unimplemented alarms
   contribute to CONFIG_GAP (operational detection gap). 1 unimplemented
   Test is noted but does not change the verdict (improvement opportunity).
   A generic assistant treats all recommendation gaps equally.

## Slash-command invocation

```
/aws:audit-resiliencehub-app-assessment
```

Or via the orchestrator:

```
/aws:pipeline
You: "audit this resilience hub assessment before our production launch"
```

The orchestrator emits
`[Phase: Audit | Skills routed: resiliencehub-app-assessment-auditor]`
and hands off to this skill for the VERDICT.

## CLI routing

```bash
node cli/bin/cli.js route "audit this resilience hub assessment"
# [Phase: Audit | Skills routed: resiliencehub-app-assessment-auditor]
```

## Live-account follow-up (optional, requires AWS CLI)

After remediating the staleness, validate the fresh assessment:

```bash
# Verify the latest assessment is now recent and Successful
aws resiliencehub list-app-assessments \
  --app-arn <arn> --reverse-order --max-results 1 \
  --profile default --output json | jq '.assessmentSummaries[0]'

# Confirm the app version is current
aws resiliencehub describe-app --app-arn <arn> \
  --profile default --output json | jq '.app.appVersion'

# Check policy attachment
aws resiliencehub describe-app --app-arn <arn> \
  --profile default --output json | jq '.app.policyArn'
```

Then monitor the fresh assessment's compliance score for 1-2 weeks to
confirm the Critical-tier settlement-svc finding was resolved.
