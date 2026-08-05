# Eval prompt: rollback-on-no-alarms

Audit the following CodeDeploy deployment group configuration for deployment
safety. Emit the standard VERDICT block (DEPLOYMENT_GROUP, VERDICT, REASON,
FINDINGS, REMEDIATION).

Application: user-profile-app
Deployment group: rollback-on-no-alarms-dg
Deployment group ID: d-rollback-on-no-alarms
Compute platform: Server
Deployment config: CodeDeployDefault.OneAtATime
Deployment style: IN_PLACE

autoRollbackConfiguration:
  enabled: true
  triggers:
    - DEPLOYMENT_FAILURE
    - DEPLOYMENT_STOP_ON_ALARM
    - DEPLOYMENT_STOP_ON_REQUEST

alarmConfiguration:
  enabled: false
  ignorePollAlarmFailure: false
  alarms: []
