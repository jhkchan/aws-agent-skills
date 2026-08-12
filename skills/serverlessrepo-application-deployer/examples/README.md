# End-to-End Example: Serverless Application Repository Deployment

A walkthrough showing how to use the `serverlessrepo-application-deployer`
skill from invocation through verification. Mirrors the structured-eval
pattern of shipping a concrete worked example per skill.

---

## Scenario

You are publishing a private SAR application named `s3-file-processor`
with a SAM template, granting a consumer account (999999999999)
deploy permission via an application policy, and deploying it in the
consumer account. The application needs:

- Application name: s3-file-processor
- SAM template: Transform: AWS::Serverless-2016-10-31
- Lambda function with S3 event trigger
- S3 bucket parameter (BucketName)
- README.md: present
- LICENSE: present (Apache-2.0)
- Semantic version: 1.0.0
- Sharing: Private + application policy (grant 999999999999)
- Author: Jacky Chan
- Labels: s3, lambda, event-driven
- Region: us-east-1
- Publisher account: 123456789012

---

## Step 1 — Invoke the skill

### Option A: Slash command

```
/aws:deploy-serverlessrepo-application
```

Then paste the requirements.

### Option B: Natural language

```
You: "Publish a serverless application named s3-file-processor
      with a SAM template. Private sharing, grant account
      999999999999 deploy permission. Version 1.0.0."
```

### Option C: CLI routing

```bash
node cli/bin/cli.js route "publish a serverless application"
```

---

## Step 2 — Skill produces the READY_TO_DEPLOY checklist

```text
SAR_APPLICATION: s3-file-processor (1.0.0)
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓] SAM template: template.yaml (Transform: AWS::Serverless-2016-10-31)
  [✓] README.md: present (S3 File Processor documentation)
  [✓] LICENSE: present (Apache-2.0)
  [✓] Packaging: sam package → s3://my-artifacts/s3-processor-1.0.0.zip
  [✓] Semantic version: 1.0.0
  [✓] Sharing: Private+Policy (granted to 999999999999)
  [✓] Application policy: PutApplicationPolicy → Principal: 999999999999, Action: CreateCloudFormationChangeSet
  [✓] Capabilities: CAPABILITY_IAM (transform auto-generates Lambda execution role)
  [✓] Parameters: BucketName (String, required)
  [✓] Nested applications: none
  [✓] Author profile: Jacky Chan, labels: s3, lambda, event-driven
  [✓] Application ARN: arn:aws:serverlessrepo:us-east-1:123456789012:apps/s3-file-processor
VERIFICATION_COMMANDS:
  aws serverlessrepo get-application --application-id arn:aws:serverlessrepo:us-east-1:123456789012:apps/s3-file-processor --region us-east-1
  aws serverlessrepo get-application-policy --application-id arn:aws:serverlessrepo:us-east-1:123456789012:apps/s3-file-processor --region us-east-1
```

---

## Step 3 — Publishing commands

```bash
# Step 1: Validate the SAM template
sam validate --template template.yaml

# Step 2: Build and package (upload code to S3)
sam build
sam package \
  --template-file template.yaml \
  --s3-bucket my-deployment-artifacts \
  --output-template-file packaged.yaml

# Step 3: Publish the application to SAR
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

# Step 4: Grant consumer account deploy permission
APP_ARN="arn:aws:serverlessrepo:us-east-1:123456789012:apps/s3-file-processor"

aws serverlessrepo put-application-policy \
  --application-id "$APP_ARN" \
  --statements '[{"StatementId":"grant-dev-account","Actions":["serverlessrepo:CreateCloudFormationChangeSet"],"Principal":{"AWS":["arn:aws:iam::999999999999:root"]}}]' \
  --region us-east-1
```

---

## Step 4 — Consumer deploys the application

```bash
# In the consumer account (999999999999)
aws serverlessrepo create-cloud-formation-change-set \
  --application-id "arn:aws:serverlessrepo:us-east-1:123456789012:apps/s3-file-processor" \
  --stack-name s3-processor-stack \
  --capabilities CAPABILITY_IAM \
  --semantic-version "1.0.0" \
  --parameter-overrides BucketName=my-processed-bucket \
  --region us-east-1

# Execute the change set (ChangeSetId from previous output)
aws cloudformation execute-change-set \
  --change-set-name "<ChangeSetId>" \
  --region us-east-1
```

---

## Step 5 — Post-deployment verification

```bash
# Verify the application is published
aws serverlessrepo get-application \
  --application-id arn:aws:serverlessrepo:us-east-1:123456789012:apps/s3-file-processor \
  --region us-east-1

# Verify the application policy
aws serverlessrepo get-application-policy \
  --application-id arn:aws:serverlessrepo:us-east-1:123456789012:apps/s3-file-processor \
  --region us-east-1

# Verify the deployed stack (in consumer account)
aws cloudformation describe-stacks \
  --stack-name s3-processor-stack \
  --query 'Stacks[0].StackStatus' \
  --region us-east-1
```

---

## What the skill catches that a naive provisioning misses

| Configuration | Naive provisioning | Skill output | Why the skill is right |
|---|---|---|---|
| Application policy | Publishes without granting consumer | PutApplicationPolicy grants 999999999999 | Consumer gets 403 without the policy grant |
| CAPABILITY_IAM | Forgets to declare | CAPABILITY_IAM declared | Transform auto-generates IAM roles |
| sam package | Publishes raw template (local CodeUri) | Packaged template with S3 URIs | Consumers cannot access local paths |
| Semantic versioning | Reuses version | New unique version each publish | Versions are immutable |
| README requirement | Forgets README | README included | SAR API requires README at publish |
| LICENSE for public | Omits LICENSE | LICENSE flagged as required for public | API rejects public publishes without LICENSE |

---

## Related artifacts

- **Skill definition:** `skills/serverlessrepo-application-deployer/SKILL.md`
- **SAM transform and deploy guide:** `skills/serverlessrepo-application-deployer/references/sam-transform-and-deploy.md`
- **Publishing and sharing guide:** `skills/serverlessrepo-application-deployer/references/sar-publishing-and-sharing.md`
- **Slash command:** `commands/aws/deploy-serverlessrepo-application.md`
- **Eval suite:** `skills/serverlessrepo-application-deployer/evals/evals.json`
- **Legacy test cases:** `skills/serverlessrepo-application-deployer/eval/test-cases.yaml`
