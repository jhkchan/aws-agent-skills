# SAM Transform and Deploy Pipeline — Serverless Application Repository Deployer

Deep reference on the SAM transform pipeline (how AWS::Serverless::*
types expand to CloudFormation-native resources, when the transform
runs, what capabilities are required), the deploy mechanism
(create-cloud-formation-change-set vs sam deploy), and the deployment
role. Loaded on demand by the skill — kept out of the main SKILL.md
body so the provisioning procedure stays scannable.

## The SAM transform macro

### What the transform does

The `Transform: AWS::Serverless-2016-10-31` directive invokes a
CloudFormation macro that expands SAM resource types into their
CloudFormation-native equivalents. The transform is a server-side
macro — it runs during CloudFormation template processing, not during
packaging.

```text
template.yaml (SAM):
  Type: AWS::Serverless::Function
    CodeUri: ./src/
    Handler: app.handler
    Runtime: python3.12
    Policies:
      - S3CrudPolicy:
          BucketName: !Ref BucketName
    Events:
      FileUpload:
        Type: S3
        Properties:
          Bucket: !Ref FileBucket

After transform (CloudFormation-native):
  1. AWS::Lambda::Function (with Code.S3Bucket/S3Key from packaged artifact)
  2. AWS::IAM::Role (auto-generated execution role with S3 CRUD policy)
  3. AWS::Lambda::Permission (allowing S3 to invoke the function)
  4. (S3 event mapping is handled via bucket notification config)
```

### When the transform runs

The transform runs at DEPLOY TIME, not at publish time:

```text
Publish flow:
  1. sam package → uploads code to S3, replaces CodeUri
  2. serverlessrepo create-application → stores the PACKAGED SAM template
  3. SAR catalog now holds the SAM template (with Transform declared)

Deploy flow (consumer side):
  1. serverlessrepo create-cloud-formation-change-set
  2. SAR fetches the stored SAM template
  3. CloudFormation invokes the SAM transform macro → expands resources
  4. CloudFormation processes the expanded template
  5. CloudFormation creates the change set with expanded resources
  6. Consumer executes the change set → stack created
```

**Key implication:** the publisher cannot pre-transform. The transform
is inherently a deploy-time operation because it may generate account-
specific resources (IAM role names, API Gateway stage names).

### SAM type expansion reference

| SAM Type | Expands To |
|---|---|
| AWS::Serverless::Function | AWS::Lambda::Function + AWS::IAM::Role + event-based AWS::Lambda::Permission |
| AWS::Serverless::Api | AWS::ApiGateway::RestApi + Deployment + Stage + Method resources |
| AWS::Serverless::HttpApi | AWS::ApiGatewayV2::Api + Stage + Integration + Route |
| AWS::Serverless::LayerVersion | AWS::Lambda::LayerVersion |
| AWS::Serverless::SimpleTable | AWS::DynamoDB::Table (with BillingMode: PAY_PER_REQUEST) |
| AWS::Serverless::Application | AWS::CloudFormation::Stack (nested stack from child SAR app) |
| AWS::Serverless::StateMachine | AWS::StepFunctions::StateMachine + AWS::IAM::Role |
| AWS::Serverless::Connector | IAM permissions wired between source and destination |
| AWS::Serverless::GraphQLApi | AWS::AppSync::GraphQLApi + DataSource + Resolver |

### Auto-generated IAM roles

When a function uses `Policies` (instead of an explicit `Role`), the
transform auto-generates an AWS::IAM::Role with the specified managed
policies. This is why CAPABILITY_IAM is required even when the SAM
template does not explicitly declare AWS::IAM::Role.

```yaml
# SAM template — no explicit IAM role
ProcessorFunction:
  Type: AWS::Serverless::Function
  Properties:
    CodeUri: ./src/
    Handler: app.handler
    Runtime: python3.12
    Policies:
      - S3CrudPolicy:
          BucketName: !Ref BucketName

# Transform generates:
#   AWS::IAM::Role "ProcessorFunctionRole"
#     with S3 CRUD permissions on the bucket
```

**SAM policy templates** ( shorthand policy generators):
- `S3CrudPolicy` — full S3 CRUD on a bucket
- `DynamoDBCrudPolicy` — full DynamoDB CRUD on a table
- `SQSPollerPolicy` — SQS receive/delete permissions
- `CloudWatchPutMetricPolicy` — CloudWatch metric publishing
- `VPCAccessPolicy` — ENI creation for Lambda VPC access
- `AcmCertificateReadPolicy` — ACM certificate describe/get

## Deploy mechanism

### Option 1: create-cloud-formation-change-set (SAR native)

The SAR-native deploy path uses the serverlessrepo API:

```bash
# Consumer deploys the app
CHANGE_SET=$(aws serverlessrepo create-cloud-formation-change-set \
  --application-id "arn:aws:serverlessrepo:us-east-1:123456789012:apps/s3-file-processor" \
  --stack-name s3-processor-stack \
  --capabilities CAPABILITY_IAM \
  --semantic-version "1.0.0" \
  --parameter-overrides BucketName=my-bucket \
  --region us-east-1 \
  --query 'ChangeSetId' --output text)

# Execute the change set
aws cloudformation execute-change-set \
  --change-set-name "$CHANGE_SET" \
  --region us-east-1
```

### Option 2: sam deploy (SAM CLI)

For apps where the consumer has the packaged template directly:

```bash
sam deploy \
  --template-file packaged.yaml \
  --stack-name s3-processor-stack \
  --capabilities CAPABILITY_IAM \
  --parameter-overrides BucketName=my-bucket \
  --s3-bucket consumer-deployment-artifacts \
  --region us-east-1
```

### Option 3: CloudFormation directly (for nested stacks)

If the app is referenced as a nested application in a parent template:

```yaml
# Parent template references the SAR app
Resources:
  NestedApp:
    Type: AWS::Serverless::Application
    Properties:
      Location:
        ApplicationId: arn:aws:serverlessrepo:us-east-1:123456789012:apps/s3-file-processor
        SemanticVersion: 1.0.0
      Parameters:
        BucketName: !Ref MyBucket
```

Deploy the parent template with CAPABILITY_AUTO_EXPAND.

## Deployment role and capabilities

### Capabilities reference

| Capability | When Required | Example |
|---|---|---|
| CAPABILITY_IAM | Transform generates IAM roles (most SAM templates) | Function with `Policies` |
| CAPABILITY_NAMED_IAM | Template creates IAM resources with custom names | Explicit role with RoleName |
| CAPABILITY_AUTO_EXPAND | Template contains nested applications | AWS::Serverless::Application |
| CAPABILITY_RESOURCE_POLICY | Template modifies resource policies | S3 bucket policy, SQS queue policy |

**Most SAR deployments need at least CAPABILITY_IAM** because the SAM
transform auto-generates IAM roles. Nested applications additionally
require CAPABILITY_AUTO_EXPAND.

### Missing capability errors

If the consumer omits a required capability:

```text
InsufficientCapabilitiesException:
  Requires capabilities: [CAPABILITY_IAM]
  Template contains IAM resources
```

**Fix:** add the capability to the `--capabilities` parameter.

## Verifying the transform (dry run)

Before publishing, verify the transform produces the expected
CloudFormation-native resources:

```bash
# Build and package locally
sam build
sam package --s3-bucket my-artifacts --output-template-file packaged.yaml

# Inspect the packaged template
cat packaged.yaml | grep -A5 "Type: AWS"

# Or use the CloudFormation transform via AWS CLI (dry run)
aws cloudformation create-change-set \
  --stack-name dry-run-test \
  --template-body file://packaged.yaml \
  --change-set-type CREATE \
  --capabilities CAPABILITY_IAM \
  --region us-east-1
# Review the change set, then delete it without executing
```

## Terraform / CDK integration

### Terraform (via AWS provider)

```hcl
# Deploy a SAR application via Terraform
resource "aws_serverlessapplicationrepository_cloudformation_stack" "processor" {
  application_id   = "arn:aws:serverlessrepo:us-east-1:123456789012:apps/s3-file-processor"
  semantic_version = "1.0.0"
  name             = "s3-processor-stack"
  capabilities     = ["CAPABILITY_IAM"]
  parameters = {
    BucketName = aws_s3_bucket.processor.bucket
  }
}
```

### CDK (via CfnInclude or sar construct)

```typescript
import * as sar from 'aws-cdk-lib/aws-sar';

const app = new sar.CfnApplication(this, 'SarApp', {
  location: {
    applicationId: 'arn:aws:serverlessrepo:us-east-1:123456789012:apps/s3-file-processor',
    semanticVersion: '1.0.0',
  },
  parameters: {
    BucketName: bucket.bucketName,
  },
});
```

## Common transform pitfalls

1. **Forgetting CAPABILITY_IAM.** The transform auto-generates IAM
   roles. Most SAM templates need CAPABILITY_IAM at deploy time.

2. **Forgetting CAPABILITY_AUTO_EXPAND for nested apps.** Templates
   with AWS::Serverless::Application require this capability. Without
   it, CloudFormation rejects the template.

3. **Publishing the raw template (with local CodeUri).** Always run
   `sam package` before publishing. The raw template's `CodeUri: ./src/`
   is not accessible to consumers.

4. **Transform errors at deploy time.** The publisher cannot catch
   transform errors because the transform runs on the consumer side.
   Always run `sam build` + `sam package` locally to validate the
   template before publishing.

5. **Version conflict on update.** Each publish must use a unique
   semantic version. Reusing a version results in ConflictException.
