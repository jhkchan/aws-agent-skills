# End-to-End Example: Elastic Beanstalk Cost Optimization

A walkthrough showing how to use the `elastic-beanstalk-environment-optimizer`
skill from invocation through optimization. Mirrors the structured-eval
pattern of shipping a concrete worked example per skill.

---

## Scenario

You are optimizing a dev Elastic Beanstalk environment that is
over-provisioned. The environment is load-balanced with expensive
instances, an unnecessary ELB, and a NAT Gateway. The optimization
migrates to single-instance topology, right-sizes the instance, and
eliminates the NAT Gateway.

- Environment: my-dev-app (e-abc123def)
- Current topology: load-balanced (2x t3.medium)
- Current cost: ~$98.73/mo (instances + ELB + NAT)
- Average CPU: 12% (over 14 days)
- Deployment policy: Immutable
- Purpose: development only (downtime acceptable)

---

## Step 1 — Invoke the skill

### Option A: Slash command

```
/aws:optimize-beanstalk-env
```

Then paste the environment details.

### Option B: Natural language

```
You: "Optimize my dev Elastic Beanstalk environment my-dev-app.
      It's load-balanced with 2x t3.medium instances, an ALB, and
      a NAT Gateway. CPU is only 12%. Brief downtime is fine."
```

### Option C: CLI routing

```bash
node cli/bin/cli.js route "optimize elastic beanstalk cost"
```

---

## Step 2 — Skill produces the OPTIMIZED assessment

```text
EB_ENV: my-dev-app (e-abc123def)
VERDICT: OPTIMIZED
OPTIMIZATIONS:
  [✓] Topology: switched from Load-balanced to Single-instance (instance count: 2 → 1)
  [✓] Instance type: t3.medium → t3.small (avg CPU 12%, well within t3.small capacity)
  [✓] Deployment policy: Immutable → All at Once (dev downtime acceptable, saves 2x deploy cost)
  [✓] NAT Gateway: eliminated (instance has public IP, uses IGW)
  [✓] Auto-scaling: min=2 max=4 desired=2 → min=1 max=1 desired=1 (no scaling for dev)
COST_IMPACT:
  Current estimated cost: ~$98.73/mo
  Optimized estimated cost: ~$15.18/mo
  Estimated savings: ~$83.55/mo (85%)
VERIFICATION_COMMANDS:
  aws elasticbeanstalk describe-configuration-settings --environment-name my-dev-app --region us-east-1
  aws ec2 describe-nat-gateways --filter Name=state,Values=available --region us-east-1
```

---

## Step 3 — Apply optimizations

```bash
# Step 1: Switch to single-instance topology
aws elasticbeanstalk update-environment \
  --environment-name my-dev-app \
  --option-settings \
    Namespace=aws:elasticbeanstalk:environment,OptionName=EnvironmentType,Value=SingleInstance \
  --region us-east-1

# Step 2: Right-size instance to t3.small
aws elasticbeanstalk update-environment \
  --environment-name my-dev-app \
  --option-settings \
    Namespace=aws:autoscaling:launchconfiguration,OptionName=InstanceType,Value=t3.small \
  --region us-east-1

# Step 3: Change deployment policy to All at Once
aws elasticbeanstalk update-environment \
  --environment-name my-dev-app \
  --option-settings \
    Namespace=aws:elasticbeanstalk:command,OptionName=DeploymentPolicy,Value=AllAtOnce \
  --region us-east-1

# Step 4: Set capacity to 1 (no auto-scaling)
aws elasticbeanstalk update-environment \
  --environment-name my-dev-app \
  --option-settings \
    Namespace=aws:autoscaling:asg,OptionName=MinSize,Value=1 \
    Namespace=aws:autoscaling:asg,OptionName=MaxSize,Value=1 \
    Namespace=aws:autoscaling:asg,OptionName=DesiredCapacity,Value=1 \
  --region us-east-1

# Step 5: Eliminate the NAT Gateway (verify public IP first!)
# Verify instance has a public IP
aws ec2 describe-instances \
  --filters Name=tag:elasticbeanstalk:environment-name,Values=my-dev-app \
  --query 'Reservations[*].Instances[*].PublicIpAddress' \
  --output text --region us-east-1

# Delete the NAT Gateway
aws ec2 delete-nat-gateway \
  --nat-gateway-id nat-xxx \
  --region us-east-1
```

---

## Step 4 — Post-optimization verification

```bash
# Verify the environment is single-instance
aws elasticbeanstalk describe-environments \
  --environment-names my-dev-app \
  --query 'Environments[0].{Name:EnvironmentName,Status:Status,Health:Health}' \
  --output table --region us-east-1

# Verify instance type
aws elasticbeanstalk describe-configuration-settings \
  --environment-name my-dev-app \
  --query 'ConfigurationSettings[0].OptionSettings[?Namespace==`aws:autoscaling:launchconfiguration` && OptionName==`InstanceType`].Value' \
  --output text --region us-east-1
# Expected: t3.small

# Verify NAT Gateway is deleted
aws ec2 describe-nat-gateways \
  --filter Name=state,Values=available \
  --query 'NatGateways[*].{Id:NatGatewayId,State:State}' \
  --output table --region us-east-1
# Expected: no NAT Gateways (or the deleted one shows as "deleted")

# Verify cost savings via Billing (check next billing cycle)
aws ce get-cost-and-usage \
  --time-period Start=2026-08-01,End=2026-08-31 \
  --granularity MONTHLY \
  --metrics BlendedCost \
  --group-by Type=DIMENSION,Key=SERVICE \
  --region us-east-1
```

---

## What the skill catches that a naive optimization misses

| Optimization | Naive approach | Skill output | Why the skill is right |
|---|---|---|---|
| Topology | Keeps load-balanced | Switches to single-instance for dev | Single-instance saves ~85% (no ELB, no NAT, 1 instance) |
| NAT Gateway | Keeps NAT Gateway | Eliminates for dev with public IP | NAT Gateway costs ~$32/mo; unnecessary with public IP + IGW |
| Deployment policy | Keeps Immutable | Changes to All at Once for dev | Immutable doubles cost during deploy; All at Once is free |
| Instance sizing | Suggests smaller instance | Suggests smaller instance + topology change | Instance size is secondary to topology for cost savings |
| Cost estimate | No quantification | Full cost breakdown with savings % | Operator needs the dollar impact to justify the change |
| Production safety | Applies dev settings to prod | Distinguishes dev vs prod optimizations | Production needs load-balanced, Immutable, NAT for HA + security |

---

## Related artifacts

- **Skill definition:** `skills/elastic-beanstalk-environment-optimizer/SKILL.md`
- **Cost and deployment guide:** `skills/elastic-beanstalk-environment-optimizer/references/cost-and-deployment.md`
- **Auto-scaling and health guide:** `skills/elastic-beanstalk-environment-optimizer/references/autoscaling-and-health.md`
- **Slash command:** `commands/aws/optimize-beanstalk-env.md`
- **Eval suite:** `skills/elastic-beanstalk-environment-optimizer/evals/evals.json`
- **Legacy test cases:** `skills/elastic-beanstalk-environment-optimizer/eval/test-cases.yaml`
