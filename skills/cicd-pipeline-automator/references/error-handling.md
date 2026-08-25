# cicd-pipeline-automator — error handling (moved from SKILL.md)

Progressive-disclosure reference. Content below was moved verbatim from SKILL.md; the agent loads it only when needed.

## Error handling — procedure-level pipeline failures

These branches describe what to do when a step in the pipeline-build or
-deploy procedure fails — not when a CLI errors, but when the pipeline
*itself* cannot safely proceed.

- **If CodeBuild fails with `ResourceNotReachable` or
  `VpcConfigInvalidParameter`:** The CodeBuild project's `vpcConfig`
  references a security group, subnet, or VPC that does not exist or
  lacks `codebuild.amazonaws.com` in its security group inbound rules.
  Detection: `aws codebuild batch-get-projects --names <project>` and
  verify each `vpcConfig.securityGroupIds` / `subnets` / `vpcId` resolves
  via `aws ec2 describe-*`. Common causes: (a) the VPC was deleted but
  the project still references it; (b) the subnet has no available IP
  addresses; (c) the security group was recreated with a new ID after
  drift. Remediation: update the project with valid IDs, OR remove
  `vpcConfig` if the build does not need VPC access (e.g., no private
  artifact repo, no internal API calls). Do NOT retry the build until
  the project config is corrected — retries will fail identically.

- **If CloudFormation `create-change-set` returns an empty change set
  (`Status: FAILED`, `StatusReason: No updates are to be performed`):**
  The template is identical to the deployed stack. This is NOT a
  failure — it means the deploy is a no-op. Detection: the pipeline
  action `ChangeSetReplace` succeeds with `executionStatus: EXECUTABLE`
  but `Status: FAILED` on the change set itself. Remediation: in the
  pipeline's deploy stage, set
  `Configuration: ChangeSetName = <name>, ActionMode:
  REPLACE_ON_CREATE` and add a manual approval OR a Lambda check that
  skips `ExecuteChangeSet` when `Status == FAILED` and `StatusReason`
  contains `No updates`. Do NOT treat as a deployment failure — surface
  as `VERDICT: NOOP_DEPLOY (stack already in sync)`.

- **If cross-account deployment fails with `AccessDenied` on
  `sts:AssumeRole` in the deploy action:** The cross-account role's
  trust policy has expired or is missing the pipeline account. Common
  causes: (a) `ExternalId` condition mismatch (the pipeline account ID
  changed, or the role was created without the correct `ExternalId`);
  (b) the trust policy Principal is the wrong ARN format
  (`arn:aws:iam::111111111111:root` vs
  `arn:aws:iam::111111111111:role/CodePipelineServiceRole`); (c) the
  role was deleted during an AWS Organizations SCP change. Remediation:
  in the target account, `aws iam get-role --role-name
  <CrossAccountDeploymentRole>` and inspect `AssumeRolePolicyDocument`.
  Fix the trust policy, then re-run the failed action — do NOT need to
  recreate the pipeline. If the role was deleted, recreate with
  `aws cloudformation create-change-set` against the original stack
  template (recover from CloudFormation drift detection history).

- **If the source action fails with `RevisionNotFoundException` on
  CodeConnections (formerly CodeStar Connections):** The connection
  host or repository was renamed, the branch was deleted, or the
  OAuth token expired. Detection:
  `aws codestar-connections get-connection-status --connection-arn
  <arn>` returns `PENDING` or `ERROR`. Remediation: re-auth the
  connection via the AWS console (CLI cannot complete the OAuth hand-
  shake), then update the source action's `RepositoryName` and
  `BranchName` to match the current remote. The pipeline cannot self-
  heal this — operator action required.

- **If the manual approval stage times out (Approval expires before
  reviewer acts):** Default approval action has no timeout, but if the
  pipeline is wired with an EventBridge schedule that auto-rejects
  after N hours (a common compliance pattern), the deploy stage will
  block until manual intervention. Detection: pipeline status
  `InProgress` for > SLA, approval action `Status: InProgress`.
  Remediation: (a) emit an SNS notification to the approver channel
  with a deep link to the console approval UI; (b) for the immediate
  run, retry with `aws codepipeline put-approval-result --pipeline-name
  <name> --stage-name <stage> --action-name <action> --result
  status=Approved`; (c) for prevention, add a second approver or
  extend the auto-reject window. Surface as `VERDICT:
  APPROVAL_GATE_TIMEOUT` with the approver principal name.
