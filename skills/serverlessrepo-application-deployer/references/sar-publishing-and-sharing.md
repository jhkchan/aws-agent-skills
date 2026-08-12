# SAR Publishing and Sharing — Serverless Application Repository Deployer

Deep reference on the publishing lifecycle (create-application,
update-application, versioning), sharing tiers (private, account-
grant via application policy, public), the application policy
mechanism for cross-account deploy, nested application sharing
requirements, and deletion/cleanup. Loaded on demand by the skill
— kept out of the main SKILL.md body so the provisioning procedure
stays scannable.

## Publishing lifecycle

### Create a new application (first version)

```bash
aws serverlessrepo create-application \
  --author "Jacky Chan" \
  --description "S3 file processor with event-driven Lambda" \
  --home-page-url "https://github.com/example/s3-processor" \
  --source-code-url "https://github.com/example/s3-processor" \
  --license-body file://LICENSE \
  --readme-body file://README.md \
  --labels "s3" "lambda" "event-driven" \
  --semantic-version "1.0.0" \
  --template-body file://packaged.yaml \
  --region us-east-1
```

**Required parameters:**
- `--author` — author name
- `--description` — short description
- `--readme-body` or `--readme-url` — README content (REQUIRED)
- `--semantic-version` — SemVer string (REQUIRED)
- `--template-body` or `--template-url` — the packaged SAM template

**Optional parameters:**
- `--license-body` or `--license-url` — LICENSE content (required for public)
- `--home-page-url` — project homepage
- `--source-code-url` — source repository
- `--labels` — search tags (max 10)

### Update an application (new version)

To publish a new version, call `create-application` again with the
`--application-id` and a NEW semantic version:

```bash
aws serverlessrepo create-application \
  --application-id "arn:aws:serverlessrepo:us-east-1:123456789012:apps/s3-file-processor" \
  --author "Jacky Chan" \
  --description "S3 file processor with event-driven Lambda" \
  --readme-body file://README.md \
  --semantic-version "1.1.0" \
  --template-body file://packaged.yaml \
  --region us-east-1
```

**Critical:** the semantic version must be unique. You cannot overwrite
version 1.0.0 — you must publish 1.1.0, 1.0.1, 2.0.0, etc.

### Update metadata (without a new version)

To update non-template metadata (README, description, labels) without
publishing a new version:

```bash
aws serverlessrepo update-application \
  --application-id "arn:aws:serverlessrepo:us-east-1:123456789012:apps/s3-file-processor" \
  --author "Jacky Chan" \
  --description "Updated description" \
  --readme-body file://README.md \
  --region us-east-1
```

## Sharing tiers

### Tier 1: PRIVATE (default)

By default, a SAR application is private. Only the publisher account
can deploy it.

```text
Visibility: Private
Deploy access: Publisher account only
Application policy: Not required
LICENSE: Not required (but recommended)
```

### Tier 2: PRIVATE + APPLICATION POLICY (account-grant)

To allow specific AWS accounts to deploy a private app, add an
application policy granting each account:

```bash
aws serverlessrepo put-application-policy \
  --application-id "arn:aws:serverlessrepo:us-east-1:123456789012:apps/s3-file-processor" \
  --statements '[
    {
      "StatementId": "grant-dev-account",
      "Actions": ["serverlessrepo:CreateCloudFormationChangeSet"],
      "Principal": {
        "AWS": ["arn:aws:iam::999999999999:root"]
      }
    },
    {
      "StatementId": "grant-staging-account",
      "Actions": ["serverlessrepo:CreateCloudFormationChangeSet"],
      "Principal": {
        "AWS": ["arn:aws:iam::888888888888:root"]
      }
    }
  ]' \
  --region us-east-1
```

**Policy actions:**
- `serverlessrepo:CreateCloudFormationChangeSet` — allows deploy
- `serverlessrepo:GetApplication` — allows viewing app details
- `serverlessrepo:SearchApplications` — allows search discovery

### Tier 3: PUBLIC

To make an app public, the publisher must:
1. Include a LICENSE file (required for public sharing).
2. Request public visibility through the AWS console or CLI.
3. AWS reviews and verifies the application.

```bash
# Check if the app is verified
aws serverlessrepo get-application \
  --application-id "arn:aws:serverlessrepo:us-east-1:123456789012:apps/s3-file-processor" \
  --query 'IsVerifiedAuthor' \
  --region us-east-1 --output text
```

Public apps are discoverable by anyone in the SAR catalog. No
application policy is needed — public implies open access.

## Application policy deep dive

### Policy structure

The application policy is a resource-based policy (similar to S3
bucket policy or KMS key policy). It defines who can perform which
actions on the application.

```json
{
  "Statements": [
    {
      "StatementId": "grant-org-accounts",
      "Actions": [
        "serverlessrepo:CreateCloudFormationChangeSet"
      ],
      "Principal": {
        "AWS": [
          "arn:aws:iam::999999999999:root",
          "arn:aws:iam::888888888888:root"
        ]
      }
    }
  ]
}
```

### Viewing the current policy

```bash
aws serverlessrepo get-application-policy \
  --application-id "arn:aws:serverlessrepo:us-east-1:123456789012:apps/s3-file-processor" \
  --region us-east-1
```

### Removing a grant

To remove a specific statement (revoke access for an account):

```bash
# Get the current policy, remove the statement, then PutApplicationPolicy
# with the updated policy. There is no DeleteApplicationPolicyStatement API.
aws serverlessrepo put-application-policy \
  --application-id "arn:aws:serverlessrepo:us-east-1:123456789012:apps/s3-file-processor" \
  --statements '[{"StatementId":"grant-dev-account","Actions":["serverlessrepo:CreateCloudFormationChangeSet"],"Principal":{"AWS":["arn:aws:iam::999999999999:root"]}}]' \
  --region us-east-1
```

## Nested application sharing

When a parent SAR application nests child SAR applications, the
consumer must have deploy permission for EACH child app.

```text
Parent app: data-pipeline-suite
  └── Child: s3-file-processor (1.0.0)
  └── Child: kinesis-forwarder (2.0.0)

Consumer deploys parent → SAR expands nested apps → consumer needs
deploy permission for BOTH child apps (via their respective
application policies or public visibility).
```

**If the consumer lacks permission for a child app**, the deploy fails
at the CAPABILITY_AUTO_EXPAND step with a 403 on the child app.

**Best practice:** when publishing a parent app that nests private
child apps, document the required child app permissions in the README.
Or make the child apps public so no additional policy is needed.

## Semantic versioning rules

SAR enforces strict semantic versioning (https://semver.org/):

| Version Component | When to Bump | Example |
|---|---|---|
| MAJOR | Breaking changes (new required params, removed resources, changed defaults) | 1.0.0 → 2.0.0 |
| MINOR | Backward-compatible features (new optional params, new resources) | 1.0.0 → 1.1.0 |
| PATCH | Backward-compatible fixes (bug fixes, template corrections) | 1.0.0 → 1.0.1 |
| prerelease | Alpha/beta/release-candidate | 1.0.0-beta, 2.0.0-rc.1 |

**Immutability:** each version is published once. SAR keeps ALL
historical versions. Consumers can pin to any version and roll back
by referencing an older one.

**Version range resolution (2024-2025 feature):** consumers can now
specify version ranges (e.g., `1.x`) in nested application references.
SAR resolves to the latest matching version at deploy time.

## Application deletion and cleanup

### Delete a deployed stack

Deleting the CloudFormation stack tears down the deployed resources:

```bash
aws cloudformation delete-stack \
  --stack-name s3-processor-stack \
  --region us-east-1
```

### Delete the SAR application

Deleting the SAR application removes it from the catalog. This does
NOT affect already-deployed stacks (they continue running):

```bash
aws serverlessrepo delete-application \
  --application-id "arn:aws:serverlessrepo:us-east-1:123456789012:apps/s3-file-processor" \
  --region us-east-1
```

**Critical:** deleting the SAR app does NOT delete:
- Already-deployed CloudFormation stacks (delete separately)
- S3 artifacts referenced by the template (delete the bucket)
- Application policies (they are deleted with the app)

## SAR vs AppRegistry

| Aspect | SAR | AppRegistry |
|---|---|---|
| Purpose | Deploy serverless applications | Group resources for metadata/tagging |
| Deploy mechanism | CloudFormation change set from SAM template | No deploy — metadata only |
| Template type | SAM (AWS::Serverless::*) | N/A |
| Sharing | Private, account-grant, public | N/A |
| Versioning | Semantic versioning | No versioning |
| Resource types | Lambda, API Gateway, Step Functions, etc. | Any AWS resource |
| Use case | Publish/deploy serverless apps | Organize existing resources by application |

**Do NOT confuse them.** SAR is for deploying serverless applications
from SAM templates. AppRegistry is for tagging and grouping existing
resources for cost allocation and governance.

## Terraform publishing example

```hcl
# Publish a SAR application via Terraform
resource "aws_serverlessapplicationrepository_application" "processor" {
  author          = "Jacky Chan"
  description     = "S3 file processor with event-driven Lambda"
  homepage_url    = "https://github.com/example/s3-processor"
  semantic_version = "1.0.0"
  source_code_url = "https://github.com/example/s3-processor"

  template_body = templatefile("packaged.yaml", {})

  labels = ["s3", "lambda", "event-driven"]
}

# Grant consumer account
resource "aws_serverlessapplicationrepository_application_policy" "grant" {
  application_id = aws_serverlessapplicationrepository_application.processor.application_id

  statements = jsonencode([
    {
      StatementId = "grant-dev-account"
      Actions     = ["serverlessrepo:CreateCloudFormationChangeSet"]
      Principal   = {
        AWS = ["arn:aws:iam::999999999999:root"]
      }
    }
  ])
}
```
