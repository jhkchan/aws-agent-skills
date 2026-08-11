# Deployment Policies — Elastic Beanstalk Deployer

Deep reference on Elastic Beanstalk deployment policies: all-at-once,
rolling, rolling with additional batch, immutable, and traffic
splitting. Includes decision criteria, capacity impact, rollback
behavior, and platform-level constraints. Loaded on demand by the
skill — kept out of the main SKILL.md body so the provisioning
procedure stays scannable.

## Policy comparison matrix

| Policy | Capacity during deploy | Downtime | Rollback mechanism | Requires ALB | Extra cost |
|---|---|---|---|---|---|
| All at once | Zero (all instances recycled) | Full fleet | Redeploy old version | No | None |
| Rolling | Reduced (batch out of service) | Partial (per batch) | Redeploy old version | No | None |
| Rolling + additional batch | Full (temp instances added) | None | Terminate temp batch | No | Temp instances |
| Immutable | Full (new ASG launched) | None | Terminate new ASG | No | Double capacity |
| Traffic splitting | Full (canary instances) | None | Automatic on health fail | Yes | Temp instances |

## All at once

Deploys the new version to ALL instances simultaneously. Every
instance is taken out of service, the new version is deployed, and
instances are put back in service.

**When to use:** development and testing environments where downtime
is acceptable. NEVER use for production.

**Rollback:** redeploy the old application version. Full downtime
during rollback.

## Rolling

Deploys in batches. A batch of instances is taken out of service, the
new version is deployed to those instances, and they are put back in
service. Then the next batch is processed.

**Capacity impact:** reduced by the batch size during the deploy. For
example, with 4 instances and a batch size of 2, 2 instances are down
during each batch — 50% capacity loss per batch.

**When to use:** production environments where some capacity reduction
is acceptable but the cost of additional instances is not.

## Rolling with additional batch

Before taking a batch out of service, Beanstalk launches a temporary
instance with the new version. Once healthy, a batch of old-version
instances is removed. This maintains full capacity throughout.

**When to use:** production environments where zero capacity loss is
required and the temporary cost of extra instances is acceptable.
This is the balanced production default.

## Immutable

Launches an entirely new Auto Scaling Group with the new version. The
old ASG continues serving traffic. Once all new instances pass health
checks, Beanstalk routes traffic to the new ASG and terminates the old
one.

**When to use:** production environments where the safest possible
deployment is required. This is the recommended production default.

**Rollback:** if health checks fail on the new ASG, Beanstalk
terminates it and the old ASG continues serving traffic. Zero impact
on the running application.

```bash
# Configure immutable deployment
aws elasticbeanstalk update-environment \
  --environment-name myapp-prod \
  --option-settings \
    Namespace=aws:elasticbeanstalk:command,OptionName=DeploymentPolicy,Value=Immutable
```

## Traffic splitting

Routes a configurable percentage of traffic to the new version via ALB
listener rules. The canary percentage and evaluation period are
configurable. If health checks fail during the canary window, Beanstalk
automatically rolls back.

**Prerequisites:** ALB (NLB and single-instance are NOT supported).

**Configuration:**
```bash
aws elasticbeanstalk update-environment \
  --environment-name myapp-prod \
  --option-settings \
    Namespace=aws:elasticbeanstalk:command,OptionName=DeploymentPolicy,Value=TrafficSplitting \
    Namespace=aws:elasticbeanstalk:traffic-splitting,OptionName=SplitPercentage,Value=10 \
    Namespace=aws:elasticbeanstalk:traffic-splitting,OptionName=EvaluationTime,Value=5
```

This routes 10% of traffic to the new version for 5 minutes. If health
checks pass, 100% of traffic is shifted. If they fail, the canary is
rolled back automatically.

## Deployment policy and managed updates interaction

Managed platform updates are suppressed during an active deployment.
If a deployment is in progress when the managed update window starts,
the update is deferred to the next window.

**Recommendation:** schedule deployments outside the managed update
window. If you must deploy during the window, disable managed updates
temporarily.

## Terraform examples

```hcl
# Immutable deployment
resource "aws_elastic_beanstalk_environment" "prod" {
  name                = "myapp-prod"
  application         = aws_elastic_beanstalk_application.myapp.name
  solution_stack_name = "64bit Amazon Linux 2023 v6.0.4 running Node.js 20"

  setting {
    namespace = "aws:elasticbeanstalk:command"
    name      = "DeploymentPolicy"
    value     = "Immutable"
  }

  setting {
    namespace = "aws:elasticbeanstalk:healthreporting:system"
    name      = "SystemType"
    value     = "enhanced"
  }
}

# Traffic splitting
resource "aws_elastic_beanstalk_environment" "canary" {
  name                = "myapp-canary"
  application         = aws_elastic_beanstalk_application.myapp.name
  solution_stack_name = "64bit Amazon Linux 2023 v6.0.4 running Node.js 20"

  setting {
    namespace = "aws:elasticbeanstalk:command"
    name      = "DeploymentPolicy"
    value     = "TrafficSplitting"
  }

  setting {
    namespace = "aws:elasticbeanstalk:traffic-splitting"
    name      = "SplitPercentage"
    value     = "10"
  }
}
```
