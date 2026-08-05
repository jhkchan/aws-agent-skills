# Eval prompt: bluegreen-immediate-termination

Audit the following CodeDeploy deployment group configuration for deployment
safety. Emit the standard VERDICT block (DEPLOYMENT_GROUP, VERDICT, REASON,
FINDINGS, REMEDIATION).

Application: realtime-chat-app
Deployment group: bluegreen-immediate-term-dg
Deployment group ID: d-bluegreen-immediate-term
Compute platform: Server
Deployment config: CodeDeployDefault.OneAtATime
Deployment style:
  deploymentType: BLUE_GREEN
  deploymentOption: WITH_TRAFFIC_CONTROL

autoRollbackConfiguration:
  enabled: true
  triggers:
    - DEPLOYMENT_FAILURE
    - DEPLOYMENT_STOP_ON_ALARM

alarmConfiguration:
  enabled: true
  ignorePollAlarmFailure: false
  alarms:
    - name: WebSocketConnectionDrop
    - name: MessageQueueDepth

blueGreenConfiguration:
  terminateBlueInstancesOnDeploymentSuccess:
    action: TERMINATE
    terminationWaitTimeInMinutes: 0
