---
description: Provision an AWS Elastic Beanstalk environment with production-grade defaults (web server or worker tier, Amazon Linux 2023 platform, deployment policies, managed updates, enhanced health, ALB/NLB, .ebextensions, CNAME swap for blue-green, RDS integration). Emits a READY_TO_DEPLOY checklist with verification commands.
nl_triggers:
  - "create elastic beanstalk"
  - "deploy elastic beanstalk"
  - "deploy beanstalk application"
  - "beanstalk environment"
  - "beanstalk blue-green"
  - "beanstalk cname swap"
  - "beanstalk worker tier"
  - "beanstalk sqs worker"
  - "beanstalk immutable deployment"
  - "ebextensions"
  - "beanstalk managed updates"
  - "elastic beanstalk"
  - "beanstalk platform amazon linux 2023"
routes_to: elastic-beanstalk-deployer
---

# /aws:deploy-elastic-beanstalk

Activate the `elastic-beanstalk-deployer` skill and provision an AWS
Elastic Beanstalk application and environment with production-grade
defaults.

## What it does

The skill walks the provisioning procedure and emits a
READY_TO_DEPLOY checklist:

1. Application and environment model (create-application, version)
2. Environment tier (web server vs worker)
3. Platform (Amazon Linux 2023, Node.js/Python/Java/Go/.NET)
4. Deployment policies (all-at-once, rolling, immutable, traffic splitting)
5. Managed platform updates (patching window)
6. Enhanced health reporting
7. Load balancer (ALB vs NLB)
8. Instance profile and service role (IAM prerequisites)
9. VPC, subnets, security groups
10. Auto scaling group (capacity and triggers)
11. .ebextensions and .platform hooks (infrastructure as code)
12. RDS integration (attached vs external)
13. CNAME swap for blue-green deployment
14. Application version lifecycle
15. Recent features (AL2023, Graviton, traffic splitting GA)

## When to use

- You need to create an Elastic Beanstalk application or environment.
- You are deploying a new application version.
- You are configuring blue-green deployment via CNAME swap.
- You are setting up a worker tier environment with SQS.
- You need .ebextensions for infrastructure as code.
- You are choosing a deployment policy.
- You are configuring managed platform updates.

## When NOT to use

- **Amazon ECS/EKS** — use container-specific skills.
- **AWS App Runner** — use the apprunner skill.
- **EC2 auto scaling groups standalone** — use EC2 skills.
- **Lambda functions** — use the Lambda deploy skill.

## How to invoke

### Slash command

```
/aws:deploy-elastic-beanstalk
```

Then provide: application name, environment name, platform/solution
stack, application version (S3 bucket/key), tier (web server/worker),
deployment policy, load balancer type, VPC/subnet IDs, security
groups, ASG min/max, managed update preferences, tags.

### Natural language

Any of these routes to the same skill:

- "create an elastic beanstalk environment for myapp"
- "deploy version v2 to my beanstalk environment"
- "set up blue-green deployment with cname swap"
- "create a worker tier environment with sqs"
- "configure immutable deployment for my beanstalk app"

### CLI routing

```bash
node cli/bin/cli.js route "create elastic beanstalk environment"
```

## Pipeline integration

This skill operates in **Phase 1 (Deploy)** of the CloudOps pipeline.
The orchestrator routes to it when the user wants to create or update
Elastic Beanstalk environments. The output checklist feeds into
verification pipelines and downstream audit skills.

## Example

```
You: /aws:deploy-elastic-beanstalk

     Create an Elastic Beanstalk environment myapp-prod for myapp
     in us-east-1. Node.js 20 on Amazon Linux 2023. Immutable
     deployment. ALB. Enhanced health. VPC vpc-aaa11122.

Skill:
  ELASTIC_BEANSTALK: myapp / myapp-prod
  VERDICT: READY_TO_DEPLOY
  CHECKLIST:
    [✓] Platform: 64bit Amazon Linux 2023 v6.0.4 running Node.js 20
    [✓] Deployment policy: Immutable
    [✓] Enhanced health: enabled
    [✓] Load balancer: ALB
    [✓] Service role: aws-elasticbeanstalk-service-role
    [✓] Instance profile: aws-elasticbeanstalk-ec2-role
  VERIFICATION_COMMANDS:
    aws elasticbeanstalk describe-environments --environment-names myapp-prod
    aws elasticbeanstalk describe-environment-health --environment-name myapp-prod
```

## References

- Skill definition: `skills/elastic-beanstalk-deployer/SKILL.md`
- Deployment policies guide: `skills/elastic-beanstalk-deployer/references/deployment-policies.md`
- .ebextensions and platforms guide: `skills/elastic-beanstalk-deployer/references/ebextensions-and-platforms.md`
- Eval suite: `skills/elastic-beanstalk-deployer/evals/evals.json`
