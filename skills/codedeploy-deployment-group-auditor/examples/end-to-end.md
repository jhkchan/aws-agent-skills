# End-to-end usage scenario: codedeploy-deployment-group-auditor

A walkthrough showing the skill auditing a CodeDeploy deployment group that
has auto-rollback and alarms properly enabled but uses AllAtATime deployment
config (CONFIG_GAP), demonstrating the ordered gate evaluation, the
AllAtATime risk reasoning, and the config-switch remediation workflow.

## Input (user prompt)

> Audit this CodeDeploy deployment group before our next production push.
> We deploy to 20 EC2 instances behind an ALB.

```
Application: search-index-app
Deployment group: prod-search-dg
Deployment group ID: d-prod-search-001
Compute platform: Server
Deployment config: CodeDeployDefault.AllAtATime
Deployment style: IN_PLACE

autoRollbackConfiguration:
  enabled: true
  triggers:
    - DEPLOYMENT_FAILURE
    - DEPLOYMENT_STOP_ON_ALARM

alarmConfiguration:
  enabled: true
  ignorePollAlarmFailure: true
  alarms:
    - name: SearchAPIErrorRate
    - name: SearchLatencyP99
```

## Skill output

```text
DEPLOYMENT_GROUP: prod-search-dg
VERDICT: CONFIG_GAP
REASON: Deployment config is CodeDeployDefault.AllAtATime — every instance is
deployed simultaneously, meaning all 20 instances are at risk during the
deployment window even though auto-rollback and alarms are enabled (Step 3).
Additionally, ignorePollAlarmFailure is true, which silently disables alarm
monitoring during CloudWatch connectivity issues.
FINDINGS:
  - [CONFIG_GAP] deploymentConfigName is CodeDeployDefault.AllAtATime (Step 3)
  - [WARNING] ignorePollAlarmFailure is true — alarm polling failures are
    silently ignored, bypassing the alarm safety net during infrastructure
    events
  - [OK] autoRollbackConfiguration enabled with DEPLOYMENT_FAILURE trigger (Step 1)
  - [OK] alarmConfiguration enabled with 2 alarms (Step 2)
REMEDIATION:
  1. CONFIG_GAP — Switch to OneAtATime: aws deploy update-deployment-group
     --application-name search-index-app
     --deployment-group-name prod-search-dg
     --deployment-config-name CodeDeployDefault.OneAtATime.
  2. WARNING — Set ignorePollAlarmFailure to false: aws deploy
     update-deployment-group --application-name search-index-app
     --deployment-group-name prod-search-dg
     --alarm-configuration
     enabled=true,ignorePollAlarmFailure=false,alarms=[{name=SearchAPIErrorRate},{name=SearchLatencyP99}].
  3. Back up the current config before changes: aws deploy
     get-deployment-group --application-name search-index-app
     --deployment-group-name prod-search-dg --output json
     > /tmp/prod-search-dg-backup.json.
```

## What the skill caught that a generic assistant misses

1. **The ordered gate evaluation.** A generic assistant might flag
   `ignorePollAlarmFailure` or the AllAtATime config without explaining
   priority. The skill evaluates rollback first, then alarms, then config —
   producing a single deterministic CONFIG_GAP verdict because the first two
   gates pass. The `ignorePollAlarmFailure` issue is surfaced as a WARNING
   (it does not change the verdict but is an operational risk).

2. **AllAtATime risk reasoning.** A generic assistant says "AllAtATime is
   risky." The skill explains that with 20 EC2 instances, AllAtATime takes
   all 20 offline simultaneously before rollback can trigger — total downtime
   = detection time + full rollback time across all instances. OneAtATime
   keeps 19 instances healthy throughout.

3. **`ignorePollAlarmFailure` as a silent failure mode.** A generic assistant
   does not flag this flag. The skill identifies that when CloudWatch is
   unreachable (the exact scenario during infrastructure events), this flag
   silently continues the deployment as if all alarms are healthy — bypassing
   the alarm safety net without any visible signal to the operator.

4. **Per-finding severity breakdown.** The verdict is CONFIG_GAP (worst
   finding), but the FINDINGS list shows individual severities: the
   AllAtATime config is CONFIG_GAP, the `ignorePollAlarmFailure` flag is a
   WARNING, and the rollback + alarm configuration is OK. This lets the
   operator triage each finding independently.

## Slash-command invocation

```
/aws:audit-codedeploy-deployment-group
```

Or via the orchestrator:

```
/aws:pipeline
You: "audit this CodeDeploy deployment group before our next push"
```

The orchestrator emits
`[Phase: Audit | Skills routed: codedeploy-deployment-group-auditor]` and
hands off to this skill for the VERDICT.

## Live-account follow-up (optional, requires AWS CLI)

After remediating the deployment config:

```bash
# Verify the deployment config was updated
aws deploy get-deployment-group \
  --application-name search-index-app \
  --deployment-group-name prod-search-dg \
  --profile default --output json | jq '.deploymentGroupInfo.deploymentConfigName'

# Confirm ignorePollAlarmFailure was set to false
aws deploy get-deployment-group \
  --application-name search-index-app \
  --deployment-group-name prod-search-dg \
  --profile default --output json | jq '.deploymentGroupInfo.alarmConfiguration'

# Run a test deployment to verify OneAtATime behavior
aws deploy create-deployment \
  --application-name search-index-app \
  --deployment-group-name prod-search-dg \
  --revision revisionType=S3,s3Location={bucket=my-bucket,key=revisions/v2.1.0.zip,bundleType=zip} \
  --profile default
```

Then monitor the deployment progress to confirm instances are deployed
one at a time, not all simultaneously.
