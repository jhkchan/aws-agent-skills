---
name: troubleshoot-codepipeline-failure
description: >-
  Slash command for the codepipeline-failure-troubleshooter skill.
  Diagnoses AWS CodePipeline execution failures across Source, Build,
  Deploy, and Approval stages — Source (CodeCommit branch deleted,
  S3 source object missing, GitHub token expired, CodeStar connection
  pending), Build (CodeBuild buildspec missing, VPC config wrong, KMS
  denied on artifact bucket, image pull failure, timeout), Deploy
  (CloudFormation change-set empty, ECS task invalid, CodeDeploy
  unhealthy, S3 deploy bucket missing), Approval timeout, and
  cross-account role trust expired. Walks get-pipeline-execution,
  list-action-executions, get-pipeline-state, batch-get-builds, and
  CloudFormation describe-stack-events. Emits ROOT_CAUSE_FOUND |
  NEED_MORE_INFO | ESCALATE with the specific failure category and
  offending config element.
skill: codepipeline-failure-troubleshooter
family: DevTools
task_type: troubleshoot
verdict_shape: "ROOT_CAUSE_FOUND | NEED_MORE_INFO | ESCALATE"
allowed-tools: Read, Bash, Grep, Glob
---

# /aws:troubleshoot-codepipeline-failure

Invoke the `codepipeline-failure-troubleshooter` skill to diagnose a
CodePipeline execution failure.

Read the skill at
`skills/codepipeline-failure-troubleshooter/SKILL.md` and follow its
diagnostic procedure to identify the root cause.

## When to use

- A pipeline execution failed and the console shows a generic
  "Failed" status with no clear cause.
- The Source action FAILED (CodeCommit branch deleted, S3 source
  object missing, GitHub token expired, CodeStar connection
  pending).
- The Build action FAILED (CodeBuild buildspec missing, VPC config
  references deleted subnets, KMS denied on the artifact bucket,
  build image pull failure, TIMED_OUT).
- The Deploy action FAILED (CloudFormation change-set empty, ECS
  task definition invalid, CodeDeploy deployment group unhealthy,
  S3 deploy bucket missing).
- The Approval action FAILED with timeout.
- A cross-account Deploy action fails with `sts:AssumeRole`
  `AccessDenied` (trust policy, KMS key policy, or bucket policy).

## Invocation

```
/aws:troubleshoot-codepipeline-failure <pipeline name / execution ID / symptom description>
```

The skill will:

1. Identify the failure category (SOURCE_STAGE_FAILED,
   BUILD_STAGE_FAILED, DEPLOY_STAGE_FAILED, APPROVAL_TIMEOUT,
   CROSS_ACCOUNT_ROLE_FAILED).
2. Request the pipeline name, execution ID, and
   `list-action-executions` output for the failed action.
3. Walk the category-specific diagnostic tree.
4. Drill into the underlying service's logs (CodeBuild phases and
   CloudWatch Logs; CloudFormation `describe-stack-events`; ECS
   `describe-tasks`; CodeDeploy `get-deployment`; CloudTrail) as
   required.
5. Map to the common root-cause catalog (15 patterns covering the
   most common CodePipeline failures).
6. Validate the proposed fix via `RetryPipelineExecution` or
   `start-pipeline-execution` before declaring fixed.
7. Emit the standard VERDICT block.

## Output shape

```text
INCIDENT: <pipeline name> in <region> — <failed stage / action>
VERDICT: ROOT_CAUSE_FOUND | NEED_MORE_INFO | ESCALATE
ROOT_CAUSE: <category name> — <specific failing config element>
EVIDENCE:
  - get-pipeline-execution: <status + summary>
  - list-action-executions: <action + lastStatusChangeReason>
  - batch-get-builds: <phaseStatus + failureReason, if Build>
  - describe-stack-events: <ResourceStatusReason, if CFN Deploy>
  - iam get-role / simulate: <trust policy / decision>
ROOT_CAUSE_CATALOG: #<N>
REMEDIATION: <specific pipeline / CodeBuild / IAM change + verification>
```

## Pre-flight

The skill requires the pipeline name (or ARN) and the region. If only
a partial name is provided, the skill will run
`aws codepipeline list-pipelines` to surface candidate pipelines. If
the user provides only a vague symptom with no pipeline name, the
skill emits `NEED_MORE_INFO`.

## References

- Skill: `skills/codepipeline-failure-troubleshooter/SKILL.md`
- Reference: `skills/codepipeline-failure-troubleshooter/references/failure-catalog-and-decision-tree.md`
- Reference: `skills/codepipeline-failure-troubleshooter/references/diagnostic-commands.md`
- AWS docs: https://docs.aws.amazon.com/codepipeline/latest/userguide/welcome.html
