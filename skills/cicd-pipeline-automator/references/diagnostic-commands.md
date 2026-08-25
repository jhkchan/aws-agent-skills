# cicd-pipeline-automator — diagnostic commands (moved from SKILL.md)

Progressive-disclosure reference. Content below was moved verbatim from SKILL.md; the agent loads it only when needed.

## Live-account pre-flight (requirement gate)

1. `aws codepipeline list-pipelines` — confirm whether a pipeline with
   the target name already exists (create vs update).
2. `aws codestar-connections list-connections` — for GitHub/GitLab
   sources, verify a connection exists in `Available` state. If
   `Pending`, the operator must complete the OAuth handshake in the
   console (cannot be automated).
3. `aws codebuild list-projects` — verify the CodeBuild project exists
   or will be created alongside the pipeline.
4. `aws codebuild list-curated-environment-images` — verify the build
   image supports the language runtime (e.g.,
   `aws/codebuild/standard:7.0` supports Node 18, Python 3.11, Java 17).
5. `aws iam get-role --role-name <deploy-role>` — verify the deploy
   role exists and its trust policy includes the deploy provider.
6. `aws kms describe-key --key-id <artifact-key>` — verify the artifact
   KMS key exists and its policy grants the pipeline role and any
   cross-account deploy roles.
7. `aws s3api get-bucket-location --bucket <artifact-bucket>` and
   `get-bucket-versioning` — verify the artifact bucket exists, has
   versioning enabled, and is in the pipeline region.
8. `aws sts get-caller-identity` on the target account (if cross-
   account) — verify the deploy role is assumable.

## Malformed input rule

**Malformed input:** if the input scenario is missing required fields
(source provider, language/runtime, deploy target), emit
`VERDICT: MANUAL_STEP_REQUIRED` with `GAP: Scenario missing required
field <field>. Provide <field> to proceed.`

## Diagnostic flows

### Pipeline not triggering

1. `get-pipeline-state` — check the latest execution status. If
   nothing recent, the trigger is broken.
2. For V1: check `PollForSourceChanges` (true = polling, false =
   event-driven). If false, verify an EventBridge rule exists on the
   source change event.
3. For V2: check `Triggers` configuration. Verify the Git filter
   matches the branch and path.
4. For CodeStar Connection: verify the connection is `Available` (not
   `Pending`). A pending connection silently stops triggering.
5. Check CloudTrail for `StartPipelineExecution` events — if the
   EventBridge rule is firing but the pipeline isn't starting, the
   rule's role may lack `codepipeline:StartPipelineExecution`.

### CodeBuild timeout

1. Check the build project's `TimeoutInMinutes` (default 60, max 480).
2. Check CloudWatch Logs for the build — identify which phase is
   hanging (install, build, post_build).
3. Common causes: dependency download stall (use S3 cache or VPC
   endpoints), integration test waiting on a slow service, build
   image pull latency (use a custom ECR-hosted image).

### CloudFormation empty change-set

1. The deploy stage fails with `No updates are to be performed`.
2. Common cause: the build output template is identical to the
   deployed stack. Either no code changed, or the build did not
   regenerate the template.
3. Fix: add a buildspec step that always touches the template (e.g.,
  update a timestamp parameter), or handle `NoChange` in the deploy
  config.

### IAM role missing permissions

1. The deploy action fails with `AccessDenied` on a specific
   resource.
2. Check the deploy role (`configuration.RoleArn`) policy — does it
   grant the action on the resource?
3. For cross-account: check both the source-account pipeline role
   AND the target-account deploy role. The pipeline role must allow
   `sts:AssumeRole`; the deploy role's trust policy must allow
   `codepipeline.amazonaws.com`.

### Artifact bucket KMS policy (cross-account)

1. The deploy action fails with `AccessDenied` on `kms:Decrypt`.
2. The artifact KMS key policy must grant the target account
   `kms:Decrypt`, `kms:GenerateDataKey`. Without this, the deploy
   role can list the bucket but cannot decrypt the staged artifact.
3. Fix: add a key policy statement granting the target account root
   principal, with delegation to the deploy role.
