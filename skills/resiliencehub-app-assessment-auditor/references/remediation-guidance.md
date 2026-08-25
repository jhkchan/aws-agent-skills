# Remediation Guidance — Resilience Hub App Assessment Auditor

Per-verdict remediation playbooks moved out of the SKILL.md body. Loaded on demand.


## Remediation guidance

### For STALE_ASSESSMENT

1. Re-run the assessment against the current app version:
   ```bash
   aws resiliencehub start-app-assessment \
     --app-arn <arn> --app-version <current-version> \
     --assessment-name fresh-$(date +%Y%m%d) \
     --policy-arn <policy-arn> --profile <p>
   ```
2. Before re-running, confirm the app version is current (Step 3). If the
   app has unpublished changes, publish first:
   `aws resiliencehub publish-app-version --app-arn <arn>`.
3. For MissionCritical workloads, schedule recurring assessments (weekly
   or bi-weekly). Resilience Hub does not auto-schedule — use EventBridge
   or a CI/CD pipeline trigger.
4. After the new assessment completes (Success), re-audit to confirm the
   fresh verdict.

### For HIGH_RISK — MissionCritical/Critical tier breach (Step 5a)

1. Review the per-component compliance details in the assessment:
   `aws resiliencehub describe-app-assessment --assessment-arn <arn>`.
   Identify the specific RTO/RPO target that the NonCompliant component
   missed.
2. Typical root causes: single-AZ deployment, missing Multi-AZ, no
   standby/replica capacity, missing auto-failover, or insufficient
   monitoring coverage. Apply the infrastructure fix.
3. Implement any pending `Alarm` recommendations for the NonCompliant
   component — alarms detect the breach in real time.
4. Re-run the assessment after remediation (see STALE_ASSESSMENT
   remediation for the CLI).

### For HIGH_RISK — systemic low score (Step 5b, score < 50)

1. This indicates systemic resiliency failure — multiple components across
   multiple tiers miss their targets. Prioritise by tier: fix
   MissionCritical/Critical breaches first, then Important, then Standard.
2. Review the resiliency policy — if the targets are intentionally strict,
   the low score is a real finding. If the targets were aspirational and
   never achievable, recalibrate the policy (but document the trade-off).
3. Implement `SDD` recommendations for recovery procedures before
   attempting `Test` recommendations — operators need runbooks before
   tests can validate them.

### For LOW_COMPLIANCE

1. Review which components are NonCompliant and their tiers. Standard or
   NonCritical tier breaches are lower priority but still warrant
   remediation.
2. Implement `Alarm` recommendations first — they provide ongoing
   detection of the conditions that produced the NonCompliant result.
3. Schedule a re-assessment after implementing remediation. Do NOT
   change the policy targets to make the score look better — that is
   compliance theatre, not resiliency improvement.

### For CONFIG_GAP

- **No assessment ever run:** start the first assessment:
  `aws resiliencehub start-app-assessment --app-arn <arn> --app-version <v>
  --policy-arn <policy> --assessment-name baseline`.
- **Failed assessment:** review the failure reason in
  `describe-app-assessment --assessment-arn <arn>`. Common causes:
  unresolved CloudFormation stacks, missing IAM permissions for resource
  enumeration, or app resources in unsupported Regions. Fix the root cause
  and re-run.
- **No policy attached:** attach a policy:
  `aws resiliencehub put-app-policy --app-arn <arn> --policy-arn <policy>`,
  or create one:
  `aws resiliencehub create-resiliency-policy --policy-name <name>
  --policy '{"MissionCritical":{"rto":300,"rpo":300},...}' --tier MissionCritical`.
- **appVersion drift:** publish the current draft and re-assess:
  `aws resiliencehub publish-app-version --app-arn <arn>` then
  `start-app-assessment`.
- **Unimplemented alarm recommendations:** implement via the recommendation
  template:
  `aws resiliencehub get-recommendation-template --template-arn <arn>`,
  then deploy the CloudWatch composite alarms via CloudFormation.

### For OK

1. No remediation required for the current posture.
2. Recommend scheduling the next assessment within 90 days (or 30 days for
   MissionCritical workloads).
3. Verify any `Test` recommendations are implemented — even an OK app
   should validate its recovery procedures periodically.
4. Review the resiliency policy annually to ensure tier-to-RTO/RPO targets
   match evolving business requirements.
