# End-to-End Example: Elastic Beanstalk Deployment

A walkthrough showing how to use the `elastic-beanstalk-deployer` skill
from invocation through verification. Mirrors the structured-eval
pattern of shipping a concrete worked example per skill.

---

## Scenario

You are provisioning a production web server Elastic Beanstalk
environment with Node.js on Amazon Linux 2023, ALB, immutable
deployment policy, and managed platform updates. The environment
needs:

- Application: myapp
- Environment: myapp-prod
- Platform: 64bit Amazon Linux 2023 v6.0.4 running Node.js 20
- Application version: v2 (s3://myapp-deploy/app-v2.zip)
- Load balancer: ALB
- Deployment policy: Immutable
- Enhanced health: enabled
- Managed updates: enabled (Mon:02:00, minor level)
- VPC: vpc-aaa11122 (subnets: subnet-aaa, subnet-bbb)
- ASG: min=2, max=8 (CPUUtilization 20-80%)

---

## Step 1 — Invoke the skill

### Option A: Slash command

```
/aws:deploy-elastic-beanstalk
```

Then paste the requirements.

### Option B: Natural language

```
You: "Create an Elastic Beanstalk environment myapp-prod for myapp
      in us-east-1. Node.js 20 on Amazon Linux 2023. Immutable
      deployment. ALB. Enhanced health. VPC vpc-aaa11122."
```

### Option C: CLI routing

```bash
node cli/bin/cli.js route "create elastic beanstalk environment"
```

---

## Step 2 — Skill produces the READY_TO_DEPLOY checklist

```text
ELASTIC_BEANSTALK: myapp / myapp-prod (e-xxx123)
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓] Application: myapp
  [✓] Environment: myapp-prod (WebServer tier)
  [✓] Platform: 64bit Amazon Linux 2023 v6.0.4 running Node.js 20
  [✓] Application version: v2 (s3://myapp-deploy/app-v2.zip)
  [✓] Service role: aws-elasticbeanstalk-service-role
  [✓] Instance profile: aws-elasticbeanstalk-ec2-role
  [✓] Load balancer: ALB
  [✓] Deployment policy: Immutable
  [✓] Enhanced health: enabled
  [✓] Managed updates: enabled (Mon:02:00 UTC, minor level)
  [✓] VPC: vpc-aaa11122 (subnets: subnet-aaa, subnet-bbb)
  [✓] ASG: min=2, max=8 (trigger: CPUUtilization 20-80%)
  [✓] Tags: Environment=production, App=myapp
VERIFICATION_COMMANDS:
  aws elasticbeanstalk describe-environments --environment-names myapp-prod
  aws elasticbeanstalk describe-environment-health --environment-name myapp-prod
  aws elasticbeanstalk describe-configuration-settings --environment-name myapp-prod
```

---

## Step 3 — Provisioning commands

```bash
# Step 1: Create the application (if it doesn't exist)
aws elasticbeanstalk create-application \
  --application-name myapp \
  --description "My Application"

# Step 2: Create the application version
aws elasticbeanstalk create-application-version \
  --application-name myapp \
  --version-label v2 \
  --source-bundle S3Bucket=myapp-deploy,S3Key=app-v2.zip

# Step 3: Create the environment
aws elasticbeanstalk create-environment \
  --application-name myapp \
  --environment-name myapp-prod \
  --solution-stack-name "64bit Amazon Linux 2023 v6.0.4 running Node.js 20" \
  --version-label v2 \
  --option-settings \
    Namespace=aws:elasticbeanstalk:command,OptionName=DeploymentPolicy,Value=Immutable \
    Namespace=aws:elasticbeanstalk:healthreporting:system,OptionName=SystemType,Value=enhanced \
    Namespace=aws:ec2:vpc,OptionName=VPCId,Value=vpc-aaa11122 \
    Namespace=aws:ec2:vpc,OptionName=Subnets,Value=subnet-aaa,subnet-bbb \
    Namespace=aws:autoscaling:asg,OptionName=MinSize,Value=2 \
    Namespace=aws:autoscaling:asg,OptionName=MaxSize,Value=8 \
    Namespace=aws:elasticbeanstalk:managedactions,OptionName=ManagedActionsEnabled,Value=true \
    Namespace=aws:elasticbeanstalk:managedactions,OptionName=PreferredStartTime,Value=Mon:02:00 \
    Namespace=aws:elasticbeanstalk:managedactions:platformaction,OptionName=UpdateLevel,Value=minor \
  --tags Key=Environment,Value=production Key=App,Value=myapp
```

---

## Step 4 — Post-deployment verification

```bash
# Environment status — should be Ready
aws elasticbeanstalk describe-environments \
  --environment-names myapp-prod \
  --query 'Environments[0].{Status:Status,Health:Health,CNAME:CNAME}'

# Environment health — should be Green
aws elasticbeanstalk describe-environment-health \
  --environment-name myapp-prod \
  --attributes HealthStatus Color Causes

# Deployment policy verification
aws elasticbeanstalk describe-configuration-settings \
  --environment-name myapp-prod \
  --query 'ConfigurationSettings[0].OptionSettings[?OptionName==`DeploymentPolicy`]'
```

---

## What the skill catches that a naive provisioning misses

| Configuration | Naive provisioning | Skill output | Why the skill is right |
|---|---|---|---|
| Deployment policy | Defaults to all-at-once | Immutable | All-at-once causes full fleet downtime; immutable preserves old fleet |
| Service role | Not verified | Verified before creation | Environment creation fails without the service role |
| Instance profile | Not verified | S3 read access verified | EC2 instances cannot pull source bundle without S3 read |
| Platform | May use deprecated AL2 | Amazon Linux 2023 | AL2 is in deprecation; AL2023 is the supported platform |
| Enhanced health | Not configured | Enabled | Required for managed updates and CNAME swap health checks |
| Managed updates | Not configured | Enabled with window | Without managed updates, platform patches are never applied |

---

## Related artifacts

- **Skill definition:** `skills/elastic-beanstalk-deployer/SKILL.md`
- **Deployment policies guide:** `skills/elastic-beanstalk-deployer/references/deployment-policies.md`
- **.ebextensions and platforms guide:** `skills/elastic-beanstalk-deployer/references/ebextensions-and-platforms.md`
- **Slash command:** `commands/aws/deploy-elastic-beanstalk.md`
- **Eval suite:** `skills/elastic-beanstalk-deployer/evals/evals.json`
- **Legacy test cases:** `skills/elastic-beanstalk-deployer/eval/test-cases.yaml`
