# IaC Pattern Library — IaC Template Automator

Full CloudFormation, CDK v2, and Terraform pattern templates and structure references, moved verbatim from SKILL.md. Loaded on demand when generating a template for one of the five canonical patterns.

## CloudFormation patterns

### Template structure (canonical)

```yaml
AWSTemplateFormatVersion: "2010-09-09"
Description: "Purpose of this stack — one sentence."
Metadata:
  Comment: "Generator: iac-template-automator. Owner: <team>."
Parameters:
  Environment:
    Type: String
    AllowedValues: [dev, stage, prod]
    Default: dev
Mappings:
  RegionConfig:
    us-east-1: { AmiId: ami-0abcdef1234567890 }
    us-west-2: { AmiId: ami-0fedcba9876543210 }
Conditions:
  IsProd: !Equals [!Ref Environment, prod]
Resources:
  # Resources here
Outputs:
  StackName:
    Description: "Stack identifier for cross-stack references."
    Value: !Ref AWS::StackName
    Export:
      Name: !Sub "${AWS::StackName}-StackName"
Rules:
  # Rule-based validation
```

### Nested stacks vs cross-stack references

| Pattern | When to use | Trade-off |
|---|---|---|
| **Nested stack** (`Type: AWS::CloudFormation::Stack`) | Tight lifecycle coupling — child always created/deleted with parent | Hard to update child independently; output values flow up only |
| **Cross-stack reference** (`Fn::ImportValue`) | Loose coupling — stacks have independent lifecycles | Exported value cannot be modified while any consumer imports it; creates dependency graph |
| **StackSets** | Deploy same template across N accounts and/or regions | Requires admin in the management account; drift detection per instance |

**Cross-stack reference pitfall:** an `Export` cannot be deleted while any
other stack imports it. To change an exported value, you must first update
all consumers to stop importing it, then update the producer, then re-add
the imports. Plan cross-stack reference changes as multi-step deployments.

### Change sets (ALWAYS preview before apply)

```bash
# Create a change set against an existing stack
aws cloudformation create-change-set \
  --stack-name prod-app \
  --change-set-name prod-app-update-$(date +%s) \
  --template-body file://template.yaml \
  --capabilities CAPABILITY_NAMED_IAM CAPABILITY_AUTO_EXPAND \
  --parameters ParameterKey=Environment,ParameterValue=prod

# Inspect changes BEFORE applying
aws cloudformation describe-change-set \
  --stack-name prod-app \
  --change-set-name prod-app-update-XXXXX \
  --query 'Changes[*].[ResourceChange.Action,ResourceChange.LogicalResourceId,ResourceChange.Replacement]'

# Look for Replacement=TRUE — these resources will be DESTROYED and RECREATED
# If any data-bearing resource (RDS, DynamoDB, S3 with data) shows TRUE,
# BLOCK the apply and require manual review.
```

### Drift detection

```bash
# Detect drift on a stack (async — takes minutes for large stacks)
aws cloudformation detect-stack-drift --stack-name prod-app

# Poll status
aws cloudformation describe-stack-drift-detection-status \
  --stack-name prod-app --stack-drift-detection-id <id>

# Get the drift report
aws cloudformation describe-stack-resource-drifts \
  --stack-name prod-app \
  --stack-resource-drift-status-filters MODIFIED DELETED
```

### CloudFormation: VPC + subnets + NAT + routes

```yaml
Resources:
  VPC:
    Type: AWS::EC2::VPC
    Properties:
      CidrBlock: 10.0.0.0/16
      EnableDnsSupport: true
      EnableDnsHostnames: true
      Tags:
        - { Key: Name, Value: !Sub "${AWS::StackName}-vpc" }
        - { Key: Environment, Value: !Ref Environment }

  InternetGateway:
    Type: AWS::EC2::InternetGateway
  InternetGatewayAttachment:
    Type: AWS::EC2::VPCGatewayAttachment
    Properties:
      VpcId: !Ref VPC
      InternetGatewayId: !Ref InternetGateway

  PublicSubnet1:
    Type: AWS::EC2::Subnet
    Properties:
      VpcId: !Ref VPC
      AvailabilityZone: !Select [0, !GetAZs ""]
      CidrBlock: 10.0.1.0/24
      MapPublicIpOnLaunch: true
      Tags:
        - { Key: Name, Value: !Sub "${AWS::StackName}-public-1" }

  # ... repeat for public-2, private-1, private-2, NAT gateway, route tables
```

### CloudFormation: Lambda + API Gateway + DynamoDB (serverless)

```yaml
Transform: AWS::Serverless-2016-10-31
Resources:
  Table:
    Type: AWS::DynamoDB::Table
    Properties:
      TableName: !Sub "${AWS::StackName}-table"
      BillingMode: PAY_PER_REQUEST
      AttributeDefinitions:
        - { AttributeName: pk, AttributeType: S }
        - { AttributeName: sk, AttributeType: S }
      KeySchema:
        - { AttributeName: pk, KeyType: HASH }
        - { AttributeName: sk, KeyType: RANGE }
      SSESpecification: { SSEEnabled: true }
      PointInTimeRecoverySpecification: { PointInTimeRecoveryEnabled: true }
      Tags:
        - { Key: Environment, Value: !Ref Environment }

  Function:
    Type: AWS::Serverless::Function
    Properties:
      CodeUri: ./src
      Handler: app.handler
      Runtime: python3.12
      MemorySize: 256
      Timeout: 30
      Environment:
        Variables:
          TABLE_NAME: !Ref Table
      Policies:
        - DynamoDBReadPolicy: { TableName: !Ref Table }
        - DynamoDBWritePolicy: { TableName: !Ref Table }
      Events:
        Api:
          Type: Api
          Properties:
            Path: /items
            Method: ANY
```

### CloudFormation: ECS Fargate + ALB

Generates `AWS::ECS::Cluster`, `AWS::ElasticLoadBalancingV2::LoadBalancer`
(ALB), two `AWS::ElasticLoadBalancingV2::TargetGroup` (one per AZ for
high-availability), `AWS::ElasticLoadBalancingV2::Listener` (443 with SSL),
`AWS::ECS::TaskDefinition` with Fargate, `AWS::ECS::Service` wired to the
target group, plus the `AWS::IAM::Role` execution and task roles scoped to
`ecs-tasks.amazonaws.com`. Always include
`AWS::ElasticLoadBalancingV2::ListenerRule` with priority and conditions.

### CloudFormation: RDS Aurora + Secrets Manager rotation

```yaml
DBCluster:
  Type: AWS::RDS::DBCluster
  Properties:
    Engine: aurora-postgresql
    EngineVersion: "16.5"
    MasterUsername: !Sub "{{resolve:secretsmanager:${DBSecret}:SecretString:username}}"
    MasterUserPassword: !Sub "{{resolve:secretsmanager:${DBSecret}:SecretString:password}}"
    DatabaseName: appdb
    StorageEncrypted: true
    DeletionProtection: !If [IsProd, true, false]
    Tags:
      - { Key: Environment, Value: !Ref Environment }

DBSecret:
  Type: AWS::SecretsManager::Secret
  Properties:
    GenerateSecretString:
      SecretStringTemplate: '{"username":"appadmin"}'
      GenerateStringKey: password
      ExcludeCharacters: '"@/\'
      PasswordLength: 32

SecretRotation:
  Type: AWS::SecretsManager::RotationSchedule
  Properties:
    SecretId: !Ref DBSecret
    RotationLambdaARN: !GetAtt RotationFunction.Arn
    RotationRules: { AutomaticallyAfterDays: 30 }
```

### CloudFormation: CloudFront + S3 + WAF

CloudFront + S3 origin with Origin Access Control (OAC, replaces the
deprecated OAI), WAFv2 web ACL with managed rule groups
(AWSManagedRulesCommonRuleSet, AWSManagedRulesSQLiRuleSet), bucket policy
scoped to `cloudfront.amazonaws.com` via service principal with
`StringEquals` on the S3 resource ARN. Default cache behavior: TLSv1.2,
forwarded values whitelist, logging to a separate S3 bucket.

## CDK patterns

### App + Stack structure (CDK v2)

```typescript
import { App, Stack, StackProps } from 'aws-cdk-lib';
import { Construct } from 'constructs';

export class AppStack extends Stack {
  constructor(scope: Construct, id: string, props?: StackProps) {
    super(scope, id, props);
    // constructs here
  }
}

const app = new App();
new AppStack(app, 'prod-app', {
  env: { account: '111111111111', region: 'us-east-1' },
  tags: { Environment: 'prod', Owner: 'platform' },
});
```

### CDK: VPC (L3 Vpc construct — preferred)

```typescript
import { Vpc, SubnetType } from 'aws-cdk-lib/aws-ec2';

const vpc = new Vpc(this, 'Vpc', {
  ipAddresses: IpAddresses.cidr('10.0.0.0/16'),
  maxAzs: 3,
  subnetConfiguration: [
    { name: 'public', subnetType: SubnetType.PUBLIC, cidrMask: 24 },
    { name: 'private', subnetType: SubnetType.PRIVATE_WITH_EGRESS, cidrMask: 24 },
    { name: 'isolated', subnetType: SubnetType.PRIVATE_ISOLATED, cidrMask: 24 },
  ],
  natGateways: 2, // prod: 2 for HA; dev: 0 or 1 for cost
  flowLogs: { CloudWatch: { trafficType: FlowTrafficType.ALL } },
});
```

The L3 `Vpc` construct creates the VPC, IGW, NAT gateways, public/private
subnets per AZ, route tables, EIPs, and S3 VPC endpoint in one call. Hand-
rolling the same in CFN or TF requires ~80 lines.

### CDK: Lambda + API Gateway + DynamoDB (L3 LambdaRestApi)

```typescript
import { LambdaRestApi } from 'aws-cdk-lib/aws-apigateway';
import { NodejsFunction } from 'aws-cdk-lib/aws-lambda-nodejs';
import { Table, BillingMode, AttributeType } from 'aws-cdk-lib/aws-dynamodb';

const table = new Table(this, 'Table', {
  partitionKey: { name: 'pk', type: AttributeType.STRING },
  sortKey: { name: 'sk', type: AttributeType.STRING },
  billingMode: BillingMode.PAY_PER_REQUEST,
  encryption: TableEncryption.AWS_MANAGED,
  pointInTimeRecovery: true,
  removalPolicy: RemovalPolicy.RETAIN_ON_UPDATE_OR_DELETE,
});

const fn = new NodejsFunction(this, 'Function', {
  runtime: Runtime.NODEJS_20_X,
  entry: 'src/handler.ts',
  handler: 'handler',
  environment: { TABLE_NAME: table.tableName },
});

table.grantReadWriteData(fn);

const api = new LambdaRestApi(this, 'Api', {
  handler: fn,
  proxy: true,
  deployOptions: { stageName: 'prod' },
});
```

### CDK: ECS Fargate + ALB (L3 ApplicationLoadBalancedFargateService)

```typescript
import { ApplicationLoadBalancedFargateService } from 'aws-cdk-lib/aws-ecs-patterns';

const service = new ApplicationLoadBalancedFargateService(this, 'Service', {
  cluster,
  memoryLimitMiB: 1024,
  cpu: 512,
  taskImageOptions: {
    image: ContainerImage.fromEcrRepository(repo, 'latest'),
    containerPort: 8080,
  },
  publicLoadBalancer: false, // internal ALB behind CloudFront
  desiredCount: 3,
});
```

### CDK: RDS Aurora + secret rotation (L2 DatabaseInstance)

```typescript
import { DatabaseCluster, DatabaseClusterEngine } from 'aws-cdk-lib/aws-rds';
import { Credentials } from 'aws-cdk-lib/aws-rds';
import { SecretRotation, SecretRotationEngine } from 'aws-cdk-lib/aws-secretsmanager-rotation';

const cluster = new DatabaseCluster(this, 'Db', {
  engine: DatabaseClusterEngine.auroraPostgres({ version: AuroraPostgresEngineVersion.VER_16_5 }),
  credentials: Credentials.fromGeneratedSecret('appadmin'),
  defaultDatabaseName: 'appdb',
  storageEncrypted: true,
  deletionProtection: true,
  writer: ClusterInstance.serverlessV2('writer'),
  readers: [ClusterInstance.serverlessV2('reader1')],
});

new SecretRotation(this, 'Rotation', {
  secret: cluster.secret!,
  rotationLambda: rotationFn,
  automaticallyAfter: Duration.days(30),
});
```

### CDK aspects (cross-cutting changes)

```typescript
import { Aspects, IAspect } from 'aws-cdk-lib';
import * as s3 from 'aws-cdk-lib/aws-s3';

class EnforceEncryptionAspect implements IAspect {
  public visit(node: Construct) {
    if (node instanceof s3.Bucket && !node.encryptionKey) {
      node.enableEncryption();
    }
  }
}

Aspects.of(app).add(new EnforceEncryptionAspect());
```

## Terraform patterns

### Provider configuration (v5)

```hcl
terraform {
  required_version = ">= 1.5.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
  backend "s3" {
    bucket         = "tf-state-prod-111111111111"
    key            = "app/terraform.tfstate"
    region         = "us-east-1"
    dynamodb_table = "tf-locks"
    encrypt        = true
  }
}

provider "aws" {
  region = var.aws_region
  default_tags {
    tags = {
      Environment = var.environment
      ManagedBy   = "terraform"
      Owner       = "platform"
    }
  }
}
```

### S3 backend with DynamoDB lock (REQUIRED for any team)

```hcl
# Bootstrapped OUT-OF-BAND (not in the same state file)
resource "aws_s3_bucket" "state" {
  bucket = "tf-state-prod-111111111111"
}

resource "aws_s3_bucket_versioning" "state" {
  bucket = aws_s3_bucket.state.id
  versioning_configuration { status = "Enabled" }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "state" {
  bucket = aws_s3_bucket.state.id
  rule { apply_server_side_encryption_by_default { sse_algorithm = "AES256" } }
}

resource "aws_dynamodb_table" "locks" {
  name         = "tf-locks"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "LockID"
  attribute {
    name = "LockID"
    type = "S"
  }
}
```

### Terraform: VPC module

```hcl
module "vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "~> 5.0"

  name = "${var.stack_name}-vpc"
  cidr = "10.0.0.0/16"

  azs             = ["us-east-1a", "us-east-1b", "us-east-1c"]
  private_subnets = ["10.0.1.0/24", "10.0.2.0/24", "10.0.3.0/24"]
  public_subnets  = ["10.0.101.0/24", "10.0.102.0/24", "10.0.103.0/24"]

  enable_nat_gateway   = var.environment == "prod" ? true : false
  single_nat_gateway   = var.environment != "prod"
  enable_dns_hostnames = true
  enable_dns_support   = true

  enable_flow_log                = true
  create_flow_log_cloudwatch_iam_role = true
  create_flow_log_cloudwatch_log_group = true

  tags = { Environment = var.environment }
}
```

### Terraform: Lambda + API Gateway + DynamoDB

Generates `aws_lambda_function`, `aws_apigatewayv2_api` (HTTP API preferred
over REST for new workloads — fewer resources, lower cost), `aws_dynamodb_table`
with `server_side_encryption { enabled = true }`, plus IAM role and policy.

### Terraform: ECS Fargate + ALB

Generates `aws_ecs_cluster`, `aws_ecs_task_definition` with `requires_compatibilities =
["FARGATE"]`, `aws_ecs_service`, `aws_lb_target_group`, `aws_lb_listener`,
`aws_lb_listener_rule`, plus the data source for the ALB. Always set
`deployment_circuit_breaker` to avoid infinite deploy loops.

### Terraform: lifecycle (plan/apply/destroy)

```bash
# Initialize providers and download modules
terraform init

# Format and validate
terraform fmt -recursive
terraform validate

# Preview changes (REQUIRED before apply)
terraform plan -out=tfplan

# Apply the planned changes (auto-approve is forbidden in prod)
terraform apply tfplan

# Destroy (NEVER run in prod without a manual confirmation gate)
terraform destroy
```

### Terraform: importing existing resources

```bash
# Import an existing resource into state
terraform import aws_s3_bucket.my_bucket my-bucket-name

# WARNING: import does NOT generate config. You must write the matching
# resource block by hand, then run terraform plan to verify no diff.

# Generate config from an imported resource (Terraform 1.5+)
terraform plan -generate-config-out=generated.tf
```
