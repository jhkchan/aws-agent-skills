# CodePipeline failure catalog and decision tree

On-demand reference for the `codepipeline-failure-troubleshooter`
skill. Loaded when the skill needs the full per-stage walk with
worked examples. The SKILL.md contains the summary table; this file
expands each category with verbatim `lastStatusChangeReason` /
`externalExecutionSummary` / build-phase examples, the diagnostic
walk, and the canonical fix.

## How to use this file

1. Identify the failed stage from `list-action-executions`.
2. Jump to the matching section below.
3. Follow the walk; cross-reference evidence with the worked example.

---

## A. SOURCE_STAGE_FAILED — source action cannot fetch the artifact

### Signature

```text
stageName: Source
actionName: <Source>
lastStatus: Failed
externalExecutionSummary: <provider-specific error>
```

### Decision tree

1. **Read the `externalExecutionSummary`.** Map to a sub-cause.
2. **Cross-reference** the source provider (CodeCommit / S3 / GitHub
   / CodeStar connection) for the specific failure.
3. **Verify the source object / branch / connection exists**
   post-fix.

### Top sub-causes

| Sub-cause | Provider | Example `externalExecutionSummary` | Fix |
|---|---|---|---|
| Branch deleted / renamed | CodeCommit | `The reference name <branch> does not exist` | Recreate branch; update pipeline `BranchName` |
| Object key missing | S3 | `Key does not exist` | Upload object; verify `S3Bucket` / `S3ObjectKey` |
| Source bucket deleted | S3 | `The bucket does not exist` | Recreate or repoint `S3Bucket` |
| Token expired / revoked | GitHub v1 | `Could not authenticate to GitHub` | Rotate PAT; update secret; migrate to CodeStar connection |
| Connection pending | CodeStar / GitHub v2 | `Connection pending` | Complete the handshake in the console |
| Repository access denied | CodeCommit / GitHub | `Access denied for repository <name>` | `iam simulate-principal-policy` on the pipeline role |
| Polling source silent | All | (no execution started) | Set `PollForSourceChanges: true`, or fix the CloudWatch Events rule |

### Worked example — GitHub v1 token expired

```text
INCIDENT: app-cicd in us-east-1 — Source action "Source" FAILED
VERDICT: ROOT_CAUSE_FOUND
ROOT_CAUSE: SOURCE_STAGE_FAILED — the GitHub v1 source action's
 personal access token (stored in Secrets Manager) expired 2 days
 ago; the last successful Source action was 92 days ago
EVIDENCE:
  - list-action-executions: action "Source" lastStatus Failed,
    externalExecutionSummary "Could not authenticate to GitHub"
  - get-pipeline Source action: Owner <org>, Repo <repo>,
    OAuthToken **** (from Secrets Manager), v1 GitHub provider
  - GitHub audit log: token flagged "Credential requires renewal"
ROOT_CAUSE_CATALOG: #3 (GitHub v1 token expired / revoked)
REMEDIATION:
  1. Generate a new GitHub PAT (repo scope), store it in the
     Secrets Manager secret the pipeline action references.
  2. Update the pipeline to reload the secret:
     aws codepipeline update-pipeline --cli-json-json file://pipeline.json
     (No structural change — the secret ARN stays the same; the
     pipeline reads the new value on the next execution.)
  3. Trigger a fresh execution:
     aws codepipeline start-pipeline-execution --name app-cicd
  4. For forward-compatibility, migrate the Source action from v1
     (PAT) to v2 (CodeStar connection) so credentials rotate
     automatically. This requires changing the action `Owner`/`Repo`
     fields to `ConnectionArn` / `FullRepositoryId`.
```

---

## B. BUILD_STAGE_FAILED — CodeBuild returns FAILED

### Signature

```text
stageName: Build
actionName: <Build>
lastStatus: Failed
externalExecutionId: <codebuild-build-id>
externalExecutionSummary: "Build failed"
```

The pipeline summary is generic. The actionable detail is in
`batch-get-builds` phases and CloudWatch Logs.

### Decision tree

1. **Read the CodeBuild build ID** from
   `list-action-executions` `externalExecutionId`.
2. **Run `batch-get-builds`** and read each phase's
   `phaseStatus` and `phaseFailureReason`.
3. **Read the failing phase's logs** from CloudWatch Logs.

### Top sub-causes

| Failing phase | Sub-cause | Fix |
|---|---|---|
| `DOWNLOAD_SOURCE` FAILED | KMS denied on artifact bucket; source object missing | Add CodeBuild role to KMS key policy; verify artifact exists |
| `INSTALL` FAILED, `BUILD_CONTAINER_UNABLE_TO_PULL` | Build image cannot be pulled (ECR auth, Docker Hub rate limit, image gone) | Use ECR mirror; grant `ecr:BatchGetImage`; fix image tag |
| `INSTALL` / `BUILD` FAILED, `buildspec not found` | `buildspec.yml` not at the configured path | Update CodeBuild project `source.buildspec` OR pipeline action `OverrideBuildspec` |
| `BUILD` FAILED (exit non-zero) | Runtime / compile error in the build script | Read CloudWatch Logs; fix the failing command |
| `TIMED_OUT` build status | `timeoutInMinutes` exceeded (default 60, max 480) | Raise `timeoutInMinutes`; enable S3 cache; parallelise |
| `UPLOAD_ARTIFACTS` FAILED after build success | KMS denied on Encrypt; artifact bucket missing | Add CodeBuild role to KMS key policy with `kms:Encrypt` |
| `DOWNLOAD_SOURCE` FAILED, VPC config | Subnet / SG deleted; referenced in `vpcConfig` | Update `vpcConfig` with valid IDs |

---

## C. DEPLOY_STAGE_FAILED — deploy provider returns FAILED

### Signature

```text
stageName: Deploy
actionName: <Deploy>
lastStatus: Failed
externalExecutionSummary: <provider-specific>
```

### Decision tree

1. **Read the deploy provider** from `get-pipeline` action
   `actionTypeId.provider`.
2. **Drill into the provider's logs.**

| Provider | Drill target | Common sub-causes |
|---|---|---|
| CloudFormation | `describe-stack-events`; delegate to cloudformation-stack-troubleshooter | Change-set empty; UPDATE_FAILED; TemplatePath wrong |
| ECS | `describe-services`, `describe-tasks` (stopped-reason) | Task definition invalid; service did not stabilize; load balancer issue |
| CodeDeploy | `get-deployment`; lifecycle events | Deployment group unhealthy; lifecycle hook failed |
| S3 | `head-bucket`; `simulate-principal-policy` | Bucket deleted; `s3:PutObject` denied |

### Worked example — CloudFormation change-set empty

```text
INCIDENT: app-cicd in us-east-1 — Deploy action "Deploy" FAILED
VERDICT: ROOT_CAUSE_FOUND
ROOT_CAUSE: DEPLOY_STAGE_FAILED — the CloudFormation change-set
 auto-generated by the Deploy action contains zero changes because
 the Build action's template.yaml output is byte-identical to the
 template currently deployed on app-platform
EVIDENCE:
  - list-action-executions: action "Deploy" lastStatus Failed,
    externalExecutionSummary "ChangeSet is empty"
  - describe-change-set: Status FAILED, StatusReason "The
    submitted information didn't contain changes. Submit fresh
    information to create a change set.", Changes []
  - get-template (app-platform): byte-identical to Build output
  - describe-stack-events: no UPDATE_FAILED (change-set never ran)
ROOT_CAUSE_CATALOG: #10 (CloudFormation change-set empty)
REMEDIATION:
  1. Confirm the Build action's output actually reflects the latest
     source commit:
     aws codepipeline get-pipeline --name app-cicd \
       --query 'pipeline.stages[?name==`Deploy`].actions[0].configuration.TemplatePath'
     Inspect the Build action's output artifact at the resolved S3
     key; diff it against the deployed template.
  2. If the templates are genuinely identical (no real change in
     this commit), configure the Deploy action to tolerate empty
     change-sets:
     - Set ActionMode to REPLACE_ON_FAILURE, OR
     - Add a build-step that detects "no diff" and short-circuits
       the Deploy stage, OR
     - Use the ChangeSetName + a manual "skip-if-empty" check in
       a prior build action.
  3. If the Build is producing a stale template, fix the upstream
     Build step (e.g., wrong `TemplatePath`, build cache masking
     the latest source).
```

---

## D. APPROVAL_TIMEOUT — manual approval never resolved

### Signature

```text
stageName: Approval (or any stage with a Manual approval action)
actionName: <Approval>
lastStatus: Failed
lastStatusChangeReason: contains "Timed out"
```

### Decision tree

1. **Check `timeoutInMinutes`** in `get-pipeline` for the Approval
   action.
2. **Check `NotificationArn`** — the SNS topic that should notify
   approvers.
3. **Verify the SNS topic has subscriptions.**

### Top sub-causes

| Sub-cause | Fix |
|---|---|
| `timeoutInMinutes` too short for the team's SLA | Raise the value; improve the notification flow |
| `NotificationArn` missing from the action config | Add the SNS topic ARN |
| SNS topic has no subscriptions | Subscribe approvers (email / Slack / Lambda) |
| Subscription endpoints are stale | Re-subscribe with current endpoints |

---

## E. CROSS_ACCOUNT_ROLE_FAILED — cross-account role trust / KMS / bucket

### Signature

```text
stageName: Deploy
actionName: <Deploy>
lastStatus: Failed
externalExecutionSummary: contains "sts:AssumeRole" or cross-account "AccessDenied"
```

### Decision tree

1. **Read the customer role ARN** from `get-pipeline` action `roleArn`.
2. **Read the trust policy** in the target account:
   `aws iam get-role --role-name <role>`.
3. **Verify the pipeline service role ARN** appears in the trust
   policy's `Statement.Principal.AWS`.
4. **For KMS-denied,** read the KMS key policy on the artifact bucket.
5. **For bucket-denied,** read the artifact bucket policy.

### Top sub-causes

| Sub-cause | Fix |
|---|---|
| Trust policy lists wrong pipeline role (rename, account ID typo) | Update `Principal.AWS` to current `metadata.pipelineExecutionRole` |
| Trust policy has external ID condition mismatch | Update or remove the stale `Condition.sts:ExternalId` |
| KMS key policy missing customer role | Add customer role with `kms:Decrypt` / `kms:Encrypt` / `kms:GenerateDataKey*` |
| Artifact bucket policy missing customer role | Add customer role with `s3:GetObject` / `s3:PutObject` / `s3:ListBucket` |
| Cross-region artifact bucket does not exist | Verify per-region artifact buckets; grant role access across regions |

### Worked example — cross-account role trust lists old pipeline role

```text
INCIDENT: app-cicd in us-east-1 (account 111111111111) — Deploy
 action "DeployCrossAccount" FAILED
VERDICT: ROOT_CAUSE_FOUND
ROOT_CAUSE: CROSS_ACCOUNT_ROLE_FAILED — the customer-managed role
 arn:aws:iam::222222222222:role/cross-acct-deploy has a trust policy
 that lists the OLD pipeline service role ARN
 (AWSCodePipelineServiceRole-old-pipeline). After the pipeline was
 renamed to app-cicd, the new service role
 (AWSCodePipelineServiceRole-app-cicd) is not in the trust policy's
 Principal.AWS, so sts:AssumeRole is denied.
EVIDENCE:
  - list-action-executions: action "DeployCrossAccount" lastStatus
    Failed, externalExecutionSummary "is not authorized to perform:
    sts:AssumeRole on resource
    arn:aws:iam::222222222222:role/cross-acct-deploy"
  - aws iam get-role cross-acct-deploy (in 222222222222):
    AssumeRolePolicyDocument Statement[0].Principal.AWS =
    arn:aws:iam::111111111111:role/AWSCodePipelineServiceRole-old-pipeline
  - get-pipeline app-cicd metadata.pipelineExecutionRole =
    arn:aws:iam::111111111111:role/AWSCodePipelineServiceRole-app-cicd
  - The mismatch is the cause — the assume cannot succeed.
ROOT_CAUSE_CATALOG: #13 (cross-account role trust missing pipeline service role)
REMEDIATION:
  1. Update the trust policy in account 222222222222 to use the
     current pipeline service role ARN:
     aws iam update-assume-role-policy --role-name cross-acct-deploy \
       --policy-document file://new-trust.json
     where new-trust.json contains:
     {
       "Version": "2012-10-17",
       "Statement": [{
         "Effect": "Allow",
         "Principal": { "AWS": "arn:aws:iam::111111111111:role/AWSCodePipelineServiceRole-app-cicd" },
         "Action": "sts:AssumeRole"
       }]
     }
  2. After IAM propagation (~30-60s), retry the failed execution:
     aws codepipeline retry-pipeline-execution --pipeline-name app-cicd \
       --pipeline-execution-id <id> --retry-mode FAILED_ACTIONS
  3. Monitor the next execution:
     aws codepipeline get-pipeline-execution --pipeline-name app-cicd \
       --pipeline-execution-id <new-id> \
       --query 'pipelineExecution.{status:status,summary:summary}'
     Expect status Succeeded.
```

---

## Cross-cutting gotchas

### The pipeline action summary is a paraphrase

The `externalExecutionSummary` is a generic phrase. The verbatim
cause lives in the underlying service: CodeBuild phase logs,
CloudFormation events, CodeDeploy lifecycle events, CloudTrail.
Always drill.

### Cross-account trust requires the role ARN, not the pipeline ARN

`sts:AssumeRole` requires an IAM principal (role or user), not a
pipeline resource. Use `metadata.pipelineExecutionRole` from
`get-pipeline`, never the pipeline ARN.

### KMS key policy is the silent killer

Even with a perfect trust policy, a cross-account deploy will fail
if the KMS key encrypting the artifact bucket does not grant the
customer role `kms:Decrypt`. The error appears as `AccessDenied` on
`s3:GetObject`, but the cause is the KMS key policy.

### CloudFormation change-set empty is not a build failure

The build succeeded; the template is identical to the deployed
state. The cause is no template diff, OR `TemplatePath` pointing at
the wrong artifact. Inspect the change-set with
`describe-change-set`.

### Polling vs event-driven source failures differ

A polling source (`PollForSourceChanges: true`) fails inside an
execution. An event-driven source (`PollForSourceChanges: false`)
fails by never starting. Read `PollForSourceChanges` first.

### RetryPipelineExecution re-runs only FAILED actions

Succeeded actions are not re-run. If the bad input came from a
succeeded Source action, you must start a new execution, not retry.

### CodeBuild timeout is on the project, not the stage

CodeBuild has its own `timeoutInMinutes` (default 60, max 480). The
pipeline stage does not have a separate timeout. Look at the
CodeBuild project setting.
