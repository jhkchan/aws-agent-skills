# Advanced Patterns — IaC Template Automator

Step 0 expert-knowledge deep dive, edge-case catalog, and recent AWS features moved verbatim from SKILL.md. Loaded on demand.

## Step 0: Expert knowledge — non-obvious IaC behaviors

These behaviors change the generated template if ignored:

- **`AWS::S3::Bucket` with no properties is public-by-default, unencrypted, unversioned.** Every S3 bucket in a generated template MUST set `BucketEncryption`, `VersioningConfiguration`, `PublicAccessBlockConfiguration`, and `LifecycleConfiguration`. CDK `Bucket` is identical — pass `encryption: BucketEncryption.KMS`, `versioned: true`, `blockPublicAccess: BlockPublicAccess.BLOCK_ALL`, and `enforceSSL: true` (via a bucket policy).

- **CloudFormation stack update can REPLACE resources.** Some property changes are not updatable in-place — CloudFormation creates a new resource, redirects references, then deletes the old. The classic foot-gun: changing an RDS `DBInstanceClass` or a DynamoDB `TableName`. Always check `Replacement=TRUE` in `describe-change-set` output before applying. This is irreversible for resources with mutable state (RDS data, DynamoDB items, S3 objects).

- **CDK synthesizes to CloudFormation — `cdk synth` is the source of truth.** The TypeScript/Python code is developer-facing; the synthesized `cdk.out/cdkstack.template.json` is what gets deployed. Debug any drift against the synthesized template, not the source code. CDK v1 produces different synthesis output than v2 — this skill targets v2 only.

- **Terraform state file (`terraform.tfstate`) is the source of truth, not the AWS API.** If someone manually changes a resource outside Terraform, the state file does not know. The next `terraform plan` shows the drift. If someone manually edits the state file (rare but catastrophic), `terraform plan` may show no drift while the real state diverges. Always use S3 backend with DynamoDB lock — never commit `.tfstate` to git.

- **`AWS::Serverless::*` resources require the SAM transform.** A CloudFormation template with `Type: AWS::Serverless::Function` MUST include `Transform: AWS::Serverless-2016-10-31` in the top-level template structure. Without the transform, `validate-template` fails with `Template format error: Unrecognized resource type`.

- **CDK L1 constructs (`CfnBucket`, `CfnFunction`) are 1:1 with CloudFormation.** L2 (`Bucket`, `Function`) add AWS-curated defaults. L3 (`ApplicationLoadBalancedFargateService`, `LambdaRestApi`) compose multiple L2s into a pattern. L3 is least code, most opinionated; L1 is most control, most code. Default to L2 for production, L3 for prototypes.

- **Terraform workspaces are NOT environments.** The Terraform docs explicitly warn: workspaces are a state-file isolation mechanism, not a substitute for separate env directories. The safe pattern is one directory per env (`envs/dev/`, `envs/prod/`) with shared modules in `modules/`. Workspaces work for isolating ephemeral test stacks within one env, not for prod-vs-dev separation.

- **`terraform import` does NOT generate config.** Importing an existing resource adds it to state but does NOT write the HCL to manage it. You must hand-write the `resource "aws_..."` block matching the imported resource, then run `terraform plan` to verify no diff. Skipping this step leaves the resource in state but unmanaged — the next apply may delete it.

- **CloudFormation Outputs are plaintext, not encrypted.** Never put secrets in `Outputs` — they are visible in the console, in CLI output, and in CloudTrail event payloads. Use `AWS::SecretsManager::Secret` and reference the secret ARN in outputs; consumers fetch the secret at runtime via `GetSecretValue`.

- **CDK `bucket.grantRead(lambda)` is convenient but coarse.** It grants `s3:GetObject` and `s3:ListBucket` on `bucket.arnForFiles('*')`. For least-privilege, narrow the key pattern: `bucket.grantRead(lambda, 'data/*.json')`. The default grants more than necessary.

- **`terraform plan` against a drifted state produces a destructive plan.** If the state file says "bucket has versioning enabled" and someone disabled it via console, `terraform plan` shows a plan to "re-enable versioning" — that looks benign. But if the state says "bucket exists" and someone DELETED it via console, `terraform plan` shows a plan to "create the bucket" — also looks benign, but data is gone. Always pair `terraform plan` with a recent `terraform show -json` to compare state vs reality.

- **CloudFormation `DeletionPolicy: Retain` keeps the resource but orphans it from the stack.** On stack delete, the resource is not deleted but the stack no longer tracks it. Re-importing it into a new stack is manual (`terraform import`-equivalent for CFN). Use `DeletionPolicy: Retain` for data stores (RDS, S3, DynamoDB), `UpdateReplacePolicy: Retain` for the same resources on replacement.

- **CDK aspects apply cross-cutting changes after construct tree construction.** An aspect like "add tags to everything" or "enforce encryption on all buckets" walks the construct tree post-build. This is powerful but order-dependent: an aspect that overrides an explicit property wins silently. Always log aspect application in a build hook.

- **Terraform `count` and `for_each` create resources that are addressable by index/key.** `count = 3` creates `aws_subnet.this[0]`, `[1]`, `[2]`. Removing an item from the middle shifts all subsequent indices, forcing Terraform to destroy-and-recreate. Use `for_each` with stable string keys for any list that may change membership.

- **CloudFormation drift detection does NOT cover all properties.** It detects drift on a subset of resource attributes — typically anything set by the customer. Service-side automatic changes (e.g., a Lambda runtime auto-update) do not register as drift. Run `describe-stack-drift-detection-status` weekly on prod stacks; do not rely on real-time drift alerts.

- **`cfn-lint` and `cfn-nag` catch different things.** `cfn-lint` checks spec compliance (correct property names, required fields, type mismatches). `cfn-nag` checks security posture (wildcard IAM, missing encryption, plaintext secrets). Run BOTH — neither is a subset of the other. The combined output is the validation surface.

- **Terraform AWS provider v5 has breaking changes from v4.** Most visible: the `s3` resource refactor (multiple small resources became one), the `default_tags` argument on the provider block, and the removal of several deprecated resources. Pin the provider version: `source = "hashicorp/aws" version = "~> 5.0"`. Do NOT upgrade without running `terraform plan` and reviewing every diff.

- **SAM CLI `sam deploy --capabilities CAPABILITY_NAMED_IAM` is required for any template that creates IAM resources.** Without it, CloudFormation rejects the create/update with `InsufficientCapabilities`. The skill always emits the required capability flag in deploy commands.

- **`AWS::CDK::Metadata` resource in synthesized templates contains construct metadata, including version info.** Some compliance frameworks flag this as information disclosure. Suppress with `cdk.json` `"metadata": {"cdk_version": false}` if your org treats CDK version as sensitive.

## Edge-case handling

- **Circular cross-stack references.** Stack A exports a value that Stack
  B imports; Stack B exports a value that Stack A imports. CloudFormation
  detects the cycle and rejects both creates. Solution: lift the shared
  resource into a third stack (Stack C) that both A and B import from.

- **Lambda runtime deprecation.** AWS announces runtime deprecations
  (e.g., nodejs16.x EOL). Generated templates MUST use a supported
  runtime (python3.12, nodejs20.x). Cross-reference
  https://docs.aws.amazon.com/lambda/latest/dg/lambda-runtimes.html for
  the current supported list.

- **Terraform provider schema cache.** `terraform validate` uses a cached
  provider schema. After upgrading the provider version, run
  `terraform init -upgrade` to refresh the cache, otherwise validate may
  report phantom errors.

- **CDK bundling requires Docker.** `NodejsFunction` and
  `PythonFunction` bundle assets via Docker. If Docker is not running,
  `cdk synth` fails with `Error: docker exited with code 1`. Provide a
  fallback or warn the operator.

- **CloudFormation template size limit.** 460,800 bytes after transforms.
  Templates approaching the limit must use nested stacks or
  `AWS::Include` transforms to split. CDK and Terraform handle this
  automatically (CDK via assets; Terraform via modules).

- **Terraform `for_each` on a list with empty values.** If `for_each =
  toset(var.list)` and the list has empty strings, Terraform errors.
  Filter with `compact(var.list)`.

## Recent AWS features (2024-2026)

- **CDK v2 default synthesizer (2024):** The new default synthesizer uses
  bootstrap roles with stricter permissions (`cdk-hnb659fds`). Teams
  migrating from v1 must re-bootstrap with the new role suffix or
  deployments fail with `NeedPerform` errors.
- **Terraform AWS provider v5 (2024):** Breaking changes from v4 — the
  S3 bucket refactor (multiple `aws_s3_bucket_*` resources consolidated
  into `aws_s3_bucket`), `default_tags` moved to provider block, several
  deprecated resources removed. Pin to `~> 5.0` and review the upgrade
  guide before migrating.
- **AWS Application Composer (2024-2025):** Visual CloudFormation designer
  in the console. Generates SAM-based templates from a drag-and-drop
  canvas. Useful for prototyping; for production, prefer text-authored
  templates for reviewability and version control.
- **CloudFormation resource import (2024):** `ImportValue`-style import
  of existing resources into a new or existing stack without disruption.
  Useful for migrating manually-provisioned resources into IaC. Pairs
  with `DeletionPolicy: Retain` for safety.
- **CDK GitOps pipeline (2024-2025):** `cdk-pipelines-github` and
  `cdk-pipelines-codepipeline` enable push-to-deploy workflows. The
  pipeline runs synth, asset upload, and `cdk deploy` across environments
  with approval gates. Generated templates should target
  `pipelines.CodePipeline` for prod-grade CD/CD.
- **CloudFormation StackSets managed execution (2024-2025):** New
  `ManagedExecution` flag enables StackSets to retry failed deployments
  to individual accounts/regions without failing the entire operation.
  Always set `ManagedExecution: { Active: true }` on org-wide StackSets.
- **Terraform 1.7+ `terraform plan -generate-config-out` (2025):**
  Generates config for imported resources, eliminating the hand-write
  step after `terraform import`. Requires Terraform 1.7+.
- **AWS SAM CLI `sam build --use-container` (2024-2025):** Builds Lambda
  packages in a Docker container matching the Lambda runtime, ensuring
  native dependency compatibility (esp. Python `cryptography`, Node
  `sharp`). Recommend for any Lambda with native deps.
