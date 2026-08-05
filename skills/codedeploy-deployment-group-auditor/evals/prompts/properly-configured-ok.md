# Eval prompt: properly-configured-ok

Audit the following CodeDeploy deployment group configuration for deployment
safety. Emit the standard VERDICT block (DEPLOYMENT_GROUP, VERDICT, REASON,
FINDINGS, REMEDIATION).

Application: billing-api-app
Deployment group: properly-configured-ok-dg
Deployment group ID: d-properly-configured-ok
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
  enabled: true
  ignorePollAlarmFailure: false
  alarms:
    - name: BillingErrorRate
    - name: BillingLatencyP99
