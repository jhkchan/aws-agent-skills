# Worked Examples — CodeDeploy Deployment Group Auditor

Load-on-demand worked examples moved verbatim from SKILL.md.

## Worked example — blue/green with 0-minute termination

```text
DEPLOYMENT_GROUP: bluegreen-immediate-term-dg
VERDICT: CONFIG_GAP
REASON: Blue/green deployment with terminationWaitTimeInMinutes of 0 —
blue instances are terminated immediately after green success (Step 4).
FINDINGS:
  - [CONFIG_GAP] terminationWaitTimeInMinutes is 0 (Step 4)
  - [OK] autoRollbackConfiguration enabled with DEPLOYMENT_FAILURE trigger (Step 1)
  - [OK] alarmConfiguration enabled with 2 alarms (Step 2)
  - [OK] deploymentConfigName is CodeDeployDefault.OneAtATime (Step 3)
  - [OK] deploymentOption is WITH_TRAFFIC_CONTROL (Step 4)
REMEDIATION:
  1. Set termination wait to at least 5 minutes: aws deploy
     update-deployment-group --application-name <app>
     --deployment-group-name bluegreen-immediate-term-dg
     --blue-green-deployment-configuration
     terminateBlueInstancesOnDeploymentSuccess={action=TERMINATE,terminationWaitTimeInMinutes=5}.
  2. If the termination block is absent entirely, the API default is 0
     minutes — always set it explicitly for production blue/green groups.
```
