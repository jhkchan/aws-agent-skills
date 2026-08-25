# Diagnostic Commands — CodeDeploy Deployment Group Auditor

Load-on-demand pre-flight and diagnostic CLI moved verbatim from SKILL.md.

## Live-account pre-flight checks

**Live-account pre-flight checks (skip for offline config audit):**
1. Verify the caller can run `deploy:GetDeploymentGroup` — the auditor role
   needs `codedeploy:GetDeploymentGroup` on the deployment group ARN.
   Remediation requires `codedeploy:UpdateDeploymentGroup` — most read-only
   auditor roles CANNOT update deployment groups. Surface this before the
   operator approves changes.
2. Verify the service role (`serviceRoleArn`) has trust relationships for the
   compute platform — EC2 needs Auto Scaling integration, ECS needs ELB +
   ECS task-set permissions.
3. Snapshot the current deployment group config before any update:
   `aws deploy get-deployment-group --application-name <app>
   --deployment-group-name <dg> --output json > /tmp/<dg>-backup.json`

## Pre-flight safety checks (run before any remediation CLI)

- **MANDATORY CONFIRMATION GATE.** Before any state-changing operation
  (`update-deployment-group`, `stop-deployment`, `create-deployment`), the
  auditor MUST emit:
  `CONFIRM: About to <action> on deployment group <dg> in application <app>.
  This affects <consequence>. Proceed? (yes/no)`
- Capture the current deployment group config for rollback:
  `aws deploy get-deployment-group --application-name <app>
  --deployment-group-name <dg> --output json >
  /tmp/<dg>-backup-$(date +%s).json`
- **Privilege-escalation warning.** Remediation commands require
  `codedeploy:UpdateDeploymentGroup` — a permission rarely held by read-only
  auditor roles. Before printing a CLI remediation, surface the exact IAM
  action needed and confirm the operator's principal holds it. Treating a
  remediation as "just run this" without IAM verification is a privilege-
  escalation footgun: the operator may run it from a role with broader
  scope than intended (e.g., a `*:*` admin fallback), bypassing guardrails.
- Verify the service role has permissions for the target compute platform
  before updating config — EC2 needs Auto Scaling, ECS needs ELB + ECS
  task-set permissions.
- Prefer enabling rollback + alarms (additive, safe for current deployment)
  over changing deployment config (which changes deployment behavior for the
  next deployment — schedule during a maintenance window).
- For CONFIG_GAP remediation (switching from AllAtATime to OneAtATime),
  schedule the next deployment during low-traffic hours — the first
  deployment under the new config may take significantly longer.
