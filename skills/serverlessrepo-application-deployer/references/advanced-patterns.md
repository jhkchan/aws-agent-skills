# Advanced Patterns — Serverless Application Repository Deployer

> Moved verbatim from SKILL.md for progressive disclosure (agentskills.io). Load on demand.

## Mindset

**One-line takeaway:** A SAR application is a SAM template + README +
LICENSE + semantic version, packaged into an S3-backed artifact,
published with a sharing scope (private, account-grant, or public),
and deployed by consumers via a CloudFormation change set. The SAM
transform converts `AWS::Serverless::*` types into CloudFormation-
native resources BEFORE CloudFormation processes the template — this
is the most misunderstood step.

Three misconceptions dominate SAR misdesign at provisioning time:

- **"Publishing a SAR app is the same as deploying a CloudFormation
  stack."** It is not. Publishing uploads the application definition
  (SAM template + artifact) to the SAR catalog. Deploying creates a
  CloudFormation stack from that definition. The SAM transform
  (AWS::Serverless-2016-10-31) runs FIRST — it expands
  `AWS::Serverless::Function`, `AWS::Serverless::Api`, etc. into
  their CloudFormation-native equivalents (AWS::Lambda::Function,
  AWS::ApiGateway::RestApi, etc.). The transformed template is what
  CloudFormation receives. This is why CAPABILITY_IAM is needed even
  when the SAM template itself does not directly declare IAM resources.

- **"Cross-account deployment works out of the box once the app is
  public."** Only partially true. A public application is discoverable
  by anyone, but deploying it in another account still requires an
  application policy (serverlessrepo:CreateCloudFormationChangeSet)
  OR the consumer to use the CreateCloudFormationTemplate API with
  explicit capabilities. For private sharing, the publisher MUST
  grant each consumer account via an application policy. Without the
  policy, the consumer gets a 403.

- **"Semantic versioning is optional for SAR."** It is NOT. Every
  publish operation REQUIRES a semantic version (e.g., 1.0.0,
  1.2.3-beta). You cannot overwrite an existing version — each
  publish must use a new version string. This is what enables update
  management: consumers pin to a version and upgrade by specifying a
  newer one.


### Configuration dependency graph — cross-dependency gotchas

- The SAM transform runs at deploy time (when the consumer calls
  create-cloud-formation-change-set), NOT at publish time. The
  publisher uploads the raw SAM template; SAR stores it; the consumer's
  deploy triggers the transform.
- CAPABILITY_AUTO_EXPAND is REQUIRED when the application uses nested
  applications (AWS::Serverless::Application). Without it, CloudFormation
  rejects the template.
- An application published as PRIVATE can only be deployed by the
  publisher account. To let another account deploy it, add an application
  policy granting that account. To let anyone deploy it, publish as PUBLIC.
- Deleting the CloudFormation stack does NOT delete the SAR application
  definition. The app remains in the catalog. To remove it, call
  DeleteApplication explicitly.
- The semantic version is part of the application's Amazon Resource
  Name (ARN). Changing the version creates a new ARN suffix; consumers
  must update their deploy reference.


## Step 12 — Deletion and cleanup

**Delete the deployed stack:**

```bash
aws cloudformation delete-stack \
  --stack-name s3-processor-stack \
  --region us-east-1
```

**Delete the application from SAR:**

```bash
aws serverlessrepo delete-application \
  --application-id "arn:aws:serverlessrepo:us-east-1:123456789012:apps/s3-file-processor" \
  --region us-east-1
```

**Critical:** deleting the CloudFormation stack does NOT delete the
SAR application definition. The app remains in the catalog. You must
call DeleteApplication explicitly. Conversely, deleting the SAR app
does NOT delete already-deployed stacks — those continue running.


## Step 13 — SAR vs AppRegistry

| Feature | SAR | AppRegistry |
|---|---|---|
| Purpose | Deploy serverless applications | Group resources for metadata/tagging |
| Deploy mechanism | CloudFormation change set from SAM template | No deploy — metadata only |
| Template type | SAM (AWS::Serverless::*) | N/A |
| Sharing | Private, account-grant, public | N/A |
| Versioning | Semantic versioning | No versioning |
| Use case | Publish/deploy Lambda-based apps | Organize existing resources by application |

**Do NOT confuse them.** SAR is a deploy surface. AppRegistry is a
metadata grouping surface.


## Step 14 — Recent features

**Recent AWS features (2023-2026):**

- **SAM CLI build improvements (2023-2024):** Enhanced `sam build`
  with esbuild support for Node.js (faster builds), and improved
  Python dependency resolution for Lambda layers.

- **SAR public app verification streamlining (2023-2024):** AWS
  simplified the verification process for public SAR applications,
  reducing review time and adding automated checks for common
  security and licensing issues.

- **Nested application dependency resolution (2024-2025):** Improved
  handling of nested application version resolution — consumers can
  now specify version ranges (e.g., `1.x`) instead of exact versions,
  with SAR resolving to the latest matching version.

- **SAM transform performance (2024-2025):** The SAM transform macro
  now runs faster for large templates (100+ resources), reducing
  deploy time for complex SAR applications.

- **Cross-region SAR deployment (2025-2026):** SAR applications can
  now be deployed across regions without re-publishing, with the
  transform handling region-specific resource properties automatically.

- **CDK SAR integration (2025-2026):** The `aws-cdk/aws-sar` construct
  (cfn-include based) allows CDK apps to deploy SAR applications
  natively, bridging the CDK and SAR ecosystems.
