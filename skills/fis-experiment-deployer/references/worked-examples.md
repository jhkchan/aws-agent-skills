# Worked Examples — FIS Experiment Deployer

Secondary worked examples, moved verbatim from SKILL.md. Load on demand.

### Perfect example output — PREREQUISITES_MISSING
```text
EXPERIMENT_TEMPLATE: ec2-stop-canary (action: aws:ec2:stop-instances, target: env=prod)
VERDICT: PREREQUISITES_MISSING
CHECKLIST:
  [✓] Intent + blast radius: Stop production instances for a drill, blast radius unknown
  [✗] Target scoped: resourceTags env=prod matches 247 instances — refusing to deploy with this filter. Switch to fis-target=true and tag only eligible resources.
  [✓] Action(s): aws:ec2:stop-instances (duration PT60S)
  [✗] Stop condition(s): no alarm name provided — without a stop condition, the experiment runs to budget with no auto-halt. Configure an error-rate or availability alarm.
  [—] IAM role: deferred until target scope is corrected
  [—] Logging: deferred
  [✗] budgetDuration: cannot set without target + stop-condition confirmation (PT2M recommended)
VERIFICATION_COMMANDS:
  aws ec2 describe-instances --filters Name=tag:env,Values=prod --query 'Reservations[*].Instances[0].InstanceId'
  aws cloudwatch describe-alarms --query 'MetricAlarms[?Namespace==`CWAgent`].AlarmName'
```

**Self-check before emit:**
- [ ] All 7 checklist rows present (no omitted items)?
- [ ] Every `[✓]` has a matching verification command?
- [ ] Target count is cited explicitly?
- [ ] Stop-condition alarm state + role permission both cited?
- [ ] IAM role cites tag conditions on action APIs?
- [ ] budgetDuration rationale ties to the action?
- [ ] Every `[✗]` cites the specific gap?
- [ ] terminate-instances (if present) carries a `[WARN]`?
