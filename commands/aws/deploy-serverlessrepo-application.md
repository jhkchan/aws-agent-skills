---
description: Publish and deploy an AWS Serverless Application Repository (SAR) application with production-grade defaults (SAM template, README, LICENSE, semantic versioning, application policy for cross-account sharing, CAPABILITY_IAM/AUTO_EXPAND, nested applications). Emits a READY_TO_DEPLOY checklist with verification commands.
nl_triggers:
  - "publish serverless application"
  - "deploy serverless application"
  - "sar publish"
  - "serverless application repository"
  - "sam deploy"
  - "sam package"
  - "sar application policy"
  - "cross-account sar deploy"
  - "nested sar application"
  - "semantic version sar"
  - "publish sar app"
  - "share serverless application"
  - "deploy from sar"
routes_to: serverlessrepo-application-deployer
---

# /aws:deploy-serverlessrepo-application

Activate the `serverlessrepo-application-deployer` skill and publish or
deploy an AWS Serverless Application Repository application with
production-grade defaults.

## What it does

The skill walks the provisioning procedure and emits a
READY_TO_DEPLOY checklist:

1. Application structure (template.yaml + README + LICENSE)
2. SAM transform pipeline (transform happens BEFORE CloudFormation)
3. Packaging (sam package → S3 artifact)
4. Semantic versioning (every publish requires a unique version)
5. Application sharing (private vs account-grant vs public)
6. Application policy (cross-account deploy permission)
7. Deployment via CloudFormation change set
8. Deployment role and capabilities (CAPABILITY_IAM / AUTO_EXPAND)
9. Nested applications (AWS::Serverless::Application)
10. Application parameters (surfaced at deploy time)
11. Author profile and labels
12. Deletion and cleanup (stack vs catalog entry)
13. SAR vs AppRegistry distinction

## When to use

- You need to publish a serverless application to SAR.
- You are sharing an application privately (account-grant) or publicly.
- You are deploying an application from SAR via CloudFormation.
- You are versioning an application update (semantic versioning).
- You are composing nested SAR applications.
- You need to configure an application policy for cross-account deploy.

## When NOT to use

- **AWS Service Catalog** — different catalog and product registration.
- **CDK app publishing** — CDK has its own publishing path (cdk publish).
- **AppRegistry** — metadata grouping, not a deploy surface.
- **ECS/EKS deployment** — use container deployment skills.

## How to invoke

### Slash command

```
/aws:deploy-serverlessrepo-application
```

Then provide: application name, SAM template file, README file,
LICENSE file (if public), semantic version, sharing scope (private/
public), consumer account IDs (for private sharing), S3 bucket for
packaging, author name, labels.

### Natural language

Any of these routes to the same skill:

- "publish a serverless application to SAR"
- "share my SAR app with another account"
- "deploy a SAR application via CloudFormation"
- "version my SAR app from 1.0.0 to 1.1.0"
- "compose nested SAR applications"

### CLI routing

```bash
node cli/bin/cli.js route "publish a serverless application"
```

## Pipeline integration

This skill operates in **Phase 1 (Deploy)** of the CloudOps pipeline.
The orchestrator routes to it when the user wants to publish or deploy
SAR applications. The output checklist feeds into verification
pipelines and downstream audit skills.

## Example

```
You: /aws:deploy-serverlessrepo-application

     Publish s3-file-processor. SAM template with Lambda + S3.
     README and LICENSE present. Version 1.0.0. Private sharing,
     grant account 999999999999. Author: Jacky Chan.

Skill:
  SAR_APPLICATION: s3-file-processor (1.0.0)
  VERDICT: READY_TO_DEPLOY
  CHECKLIST:
    [✓] SAM template: template.yaml (Transform: AWS::Serverless-2016-10-31)
    [✓] README.md: present
    [✓] LICENSE: present (Apache-2.0)
    [✓] Semantic version: 1.0.0
    [✓] Sharing: Private+Policy (granted to 999999999999)
    [✓] Capabilities: CAPABILITY_IAM
  VERIFICATION_COMMANDS:
    aws serverlessrepo get-application --application-id <arn> --region us-east-1
    aws serverlessrepo get-application-policy --application-id <arn> --region us-east-1
```

## References

- Skill definition: `skills/serverlessrepo-application-deployer/SKILL.md`
- SAM transform and deploy guide: `skills/serverlessrepo-application-deployer/references/sam-transform-and-deploy.md`
- Publishing and sharing guide: `skills/serverlessrepo-application-deployer/references/sar-publishing-and-sharing.md`
- Eval suite: `skills/serverlessrepo-application-deployer/evals/evals.json`
