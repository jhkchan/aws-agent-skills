# Error Handling — Serverless Application Repository Deployer

> Moved verbatim from SKILL.md for progressive disclosure (agentskills.io). Load on demand.

### ### CreateApplication fails with

### CreateApplication fails with "README content is required"
- The `--readme-body` parameter was not provided. SAR requires README
  content at publish time. Provide it via `--readme-body file://README.md`.

### CreateApplication fails with ConflictException
- The semantic version already exists. Each publish must use a unique
  version. Increment the version (e.g., 1.0.0 → 1.0.1) and retry.

### Consumer deploy fails with 403 Forbidden
- The application policy does not grant the consumer account. For
  private apps, call PutApplicationPolicy with the consumer's account
  ARN and the `serverlessrepo:CreateCloudFormationChangeSet` action.

### Consumer deploy fails with "Requires capabilities: [CAPABILITY_AUTO_EXPAND]"
- The template contains nested applications (AWS::Serverless::Application).
  Add CAPABILITY_AUTO_EXPAND to the `--capabilities` parameter.

### Consumer deploy fails with "Transform failed"
- The SAM template has an error (e.g., invalid resource property).
  Run `sam validate` and `sam build` locally to catch transform errors
  before publishing.

### sam package fails with "Unable to upload artifact"
- The S3 bucket does not exist or the publisher lacks `s3:PutObject`
  permission. Verify the bucket exists and the IAM policy includes
  `s3:PutObject` on the bucket.
