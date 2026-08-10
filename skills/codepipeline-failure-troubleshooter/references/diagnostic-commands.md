# CodePipeline diagnostic command reference

Canonical command script for the `codepipeline-failure-troubleshooter`
skill. Run these in order; each command's output narrows the decision
tree.

## 1. Identify the failing pipeline and execution

```bash
aws codepipeline list-pipeline-executions --pipeline-name <name> \
  --query 'pipelineExecutionSummaries[?status==`Failed`].{id:pipelineExecutionId,start:startTime,summary:summary}' \
  --output table
```

If you don't know the pipeline name:

```bash
aws codepipeline list-pipelines \
  --query 'pipelines[*].{name:name,updated:updated}'
```

## 2. List the failed actions in an execution

```bash
aws codepipeline list-action-executions --pipeline-name <name> \
  --filter '{"pipelineExecutionId": "<id>"}' \
  --query 'actionExecutionDetails[?status==`Failed`].{stage:stageName,action:actionName,status:status,reason:lastStatusChangeReason,external:externalExecutionSummary,externalExecId:externalExecutionId,lastUpdate:lastUpdatedTime}' \
  --output table
```

The earliest failed action by `lastUpdatedTime` is the cause; later
stages may have failed as a cascade.

## 3. Read the pipeline definition

```bash
aws codepipeline get-pipeline --name <name> \
  --query '{role:metadata.pipelineExecutionRole,stages:pipeline.stages[*].{name:name,actions:actions[*].{name:name,type:actionTypeId,config:configuration,role:roleArn,region:region}}}'
```

For a specific failing action's configuration:

```bash
aws codepipeline get-pipeline --name <name> \
  --query "pipeline.stages[?name=='<stage>'].actions[?name=='<action>'].{type:actionTypeId,config:configuration,role:roleArn}"
```

## 4. For BUILD_STAGE_FAILED: read CodeBuild phases and logs

```bash
# Read the build phases (find the failing phase):
aws codebuild batch-get-builds --ids <build-id> \
  --query 'builds[0].{status:buildStatus,project:projectName,timeout:timeoutInMinutes,phases:phases[*].{type:phaseType,status:phaseStatus,duration:durationInSeconds,start:startTime,end:endTime,reason:phaseFailureReason,contexts:contexts},env:environment,artifacts:artifacts,outputArtifacts:exportedEnvironmentVariables,logs:logs}'

# Read the failing phase's logs:
aws logs get-log-events \
  --log-group-name /aws/codebuild/<project-name> \
  --log-stream-name <stream> \
  --start-from-head \
  --limit 200 \
  --query 'events[*].message'
```

Phase status cheat sheet:

- `DOWNLOAD_SOURCE` FAILED → KMS / bucket / IAM on the input artifact
- `INSTALL` FAILED with `BUILD_CONTAINER_UNABLE_TO_PULL` → image pull
- `INSTALL` / `BUILD` FAILED with `BUILD_CONTAINER_FAILED` → runtime
  error (check logs); often `buildspec not found`
- `UPLOAD_ARTIFACTS` FAILED after build success → KMS Encrypt denied
- `TIMED_OUT` build status → exceeded `timeoutInMinutes`

## 5. For SOURCE_STAGE_FAILED: verify the source provider

### CodeCommit

```bash
aws codecommit get-branch --repository-name <name> --branch-name <branch>
```

If the branch does not exist, recreate it or update the pipeline's
`BranchName`.

### S3 source

```bash
aws s3api head-object --bucket <name> --key <key>
aws s3api head-bucket --bucket <name>
```

### GitHub v1 (PAT)

Check the secret value's flag in the GitHub security audit log. The
PAT is stored in Secrets Manager and referenced by the pipeline's
`OAuthToken` field. Rotate the PAT in GitHub, update the secret, and
reload the pipeline.

### CodeStar connection / GitHub v2

```bash
aws codestar-connections get-connection --connection-arn <arn> \
  --query 'Connection.{name:ConnectionName,status:ConnectionStatus,provider:ProviderType}'
```

`PENDING` means the handshake was never completed. `AVAILABLE` means
the connection is healthy.

## 6. For DEPLOY_STAGE_FAILED: drill into the deploy provider

### CloudFormation provider

```bash
# Read the auto-generated change-set:
aws cloudformation describe-change-set --stack-name <stack> \
  --change-set-name <change-set-name> \
  --query '{status:Status,reason:StatusReason,changes:Changes[*].{logical:ResourceChange.LogicalResourceId,action:ResourceChange.Action,replacement:ResourceChange.Replacement}}'

# If the change-set executed and the stack failed:
aws cloudformation describe-stack-events --stack-name <stack> \
  --query 'reverse(StackEvents[?ResourceStatus==`UPDATE_FAILED` || ResourceStatus==`CREATE_FAILED`])[-1].{logical:LogicalResourceId,reason:ResourceStatusReason,ts:Timestamp}' \
  --output table
```

Delegate the deeper CFN diagnosis to the
cloudformation-stack-troubleshooter skill.

### ECS provider

```bash
aws ecs describe-services --cluster <cluster> --services <service> \
  --query 'services[0].{desired:desiredCount,running:runningCount,events:events[:5]}'

# Identify stopped tasks and their stopped-reason:
aws ecs list-tasks --cluster <cluster> --service-name <service> --desired-status STOPPED
aws ecs describe-tasks --cluster <cluster> --tasks <task-id> \
  --query 'tasks[0].{status:lastStatus,stoppedReason:stoppedReason,stoppedAt:stoppedAt,containers:containers[*].{name:name,lastStatus:lastStatus,reason:reason}}'
```

### CodeDeploy provider

```bash
aws codedeploy get-deployment --deployment-id <id> \
  --query 'deploymentInfo.{status:status,overview:deploymentOverview,errorInformation:errorInformation}'

# Per-instance lifecycle events:
aws codedeploy list-deployment-instances --deployment-id <id>
aws codedeploy get-deployment-instance --deployment-id <id> --instance-id <i-id>
```

### S3 provider

```bash
aws s3api head-bucket --bucket <deploy-bucket>
aws iam simulate-principal-policy \
  --policy-source-arn <pipeline-role-arn> \
  --action-names s3:PutObject \
  --resource-arns arn:aws:s3:::<deploy-bucket>/*
```

## 7. For CROSS_ACCOUNT_ROLE_FAILED: trust + KMS + bucket

```bash
# Read the customer-managed role ARN from the pipeline action:
aws codepipeline get-pipeline --name <name> \
  --query "pipeline.stages[?name=='<stage>'].actions[?name=='<action>'].roleArn"

# Read the pipeline service role to compare:
aws codepipeline get-pipeline --name <name> \
  --query 'metadata.pipelineExecutionRole'

# Read the customer role's trust policy in the target account:
aws iam get-role --role-name <cross-acct-role> \
  --query 'Role.AssumeRolePolicyDocument' --output json | jq

# Verify the pipeline service role ARN is in Principal.AWS; if not,
# update the trust policy:
aws iam update-assume-role-policy --role-name <cross-acct-role> \
  --policy-document file://new-trust.json

# For KMS-denied, read the key policy on the artifact bucket:
aws kms describe-key --key-id <artifact-key-id> \
  --query 'KeyMetadata.{arn:Arn,enabled:Enabled,policyViewable:KeyUsage}'
aws kms get-key-policy --key-id <artifact-key-id> --policy-name default \
  --query 'Policy' --output text | jq

# For bucket-denied, read the artifact bucket policy:
aws s3api get-bucket-policy --bucket <artifact-bucket> \
  --query 'Policy' --output text | jq
```

## 8. For APPROVAL_TIMEOUT: check the notification target

```bash
aws codepipeline get-pipeline --name <name> \
  --query "pipeline.stages[?name=='<stage>'].actions[?name=='<action>'].configuration.{notifArn:NotificationArn,timeout:CustomData,externalEntity:ExternalEntityLink}"

# Verify the SNS topic exists and has subscriptions:
aws sns get-topic-attributes --topic-arn <notif-arn>
aws sns list-subscriptions-by-topic --topic-arn <notif-arn>
```

## 9. Validate the fix via retry or fresh execution

```bash
# For pipeline-definition changes (Source / Build path, role ARN):
aws codepipeline start-pipeline-execution --name <name>

# For fixes that do NOT change the pipeline definition (token rotation,
# trust policy update, KMS key policy update) — retry only the failed
# actions:
aws codepipeline retry-pipeline-execution --pipeline-name <name> \
  --pipeline-execution-id <id> \
  --retry-mode FAILED_ACTIONS

# Monitor the new execution:
aws codepipeline get-pipeline-execution --pipeline-name <name> \
  --pipeline-execution-id <new-id> \
  --query 'pipelineExecution.{status:status,summary:summary,updated:lastUpdateTime}'
```

## 10. Migrate GitHub v1 source to CodeStar connection (v2)

Forward-looking fix to eliminate PAT-expiry failures:

```bash
# Create the connection in the console (one-time handshake):
aws codestar-connections create-connection \
  --connection-name <name> --provider-type GitHub \
  --query 'ConnectionArn'

# Update the pipeline Source action from v1 to v2:
# - actionTypeId.Provider: GitHub → CodeStarSourceConnection
# - configuration.Owner/Repo/Branch → CodeStarConnectionArn +
#   FullRepositoryId + BranchName
# Apply via update-pipeline with the new action structure.
```

After the migration, credential rotation is handled by the CodeStar
connection, eliminating the PAT-expiry failure mode.
