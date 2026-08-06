# Eval prompt: rollback-disabled-alarms-on

Audit the following CodeDeploy deployment group configuration for deployment
safety. Emit the standard VERDICT block (DEPLOYMENT_GROUP, VERDICT, REASON,
FINDINGS, REMEDIATION).

Application: checkout-service-app
Deployment group: rollback-disabled-dg
Deployment group ID: d-rollback-disabled
Compute platform: Server
Deployment config: CodeDeployDefault.OneAtATime
Deployment style: IN_PLACE

autoRollbackConfiguration:
  enabled: false
  triggers: []

alarmConfiguration:
  enabled: true
  ignorePollAlarmFailure: false
  alarms:
    - name: HighErrorRate
    - name: ElevatedLatency
