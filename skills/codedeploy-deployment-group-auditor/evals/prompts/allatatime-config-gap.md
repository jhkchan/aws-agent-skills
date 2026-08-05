# Eval prompt: allatatime-config-gap

Audit the following CodeDeploy deployment group configuration for deployment
safety. Emit the standard VERDICT block (DEPLOYMENT_GROUP, VERDICT, REASON,
FINDINGS, REMEDIATION).

Application: search-index-app
Deployment group: allatatime-config-gap-dg
Deployment group ID: d-allatatime-config-gap
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
  ignorePollAlarmFailure: false
  alarms:
    - name: SearchAPIErrorRate
    - name: SearchLatencyP99
