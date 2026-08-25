# Diagnostic Commands — Elastic Beanstalk Environment Optimizer

Read-only inspection commands moved verbatim from SKILL.md. Loaded on demand.

## Opt 1 — CloudWatch right-sizing metric command (from SKILL.md)

```bash
# Get average CPU utilization over 14 days
aws cloudwatch get-metric-statistics \
  --namespace AWS/EC2 \
  --metric-name CPUUtilization \
  --dimensions Name=InstanceId,Values=i-aaa111222 \
  --start-time $(date -u -d '14 days ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 86400 \
  --statistics Average Maximum \
  --output table --region us-east-1

# Right-sizing heuristic:
#   Average CPU < 20%  → instance is 2x+ over-provisioned (downsize)
#   Average CPU 20-40% → some room to downsize (one size smaller)
#   Average CPU 40-70% → well-provisioned (keep)
#   Average CPU > 70%  → under-provisioned (upsize)
```

## Opt 4 — read current deployment policy (from SKILL.md)

```bash
aws elasticbeanstalk describe-configuration-settings \
  --environment-name my-env \
  --query 'ConfigurationSettings[0].OptionSettings[?Namespace==`aws:elasticbeanstalk:command`]' \
  --output table --region us-east-1
```

## Opt 5 — read current managed update config (from SKILL.md)

```bash
aws elasticbeanstalk describe-configuration-settings \
  --environment-name my-env \
  --query 'ConfigurationSettings[0].OptionSettings[?Namespace==`aws:elasticbeanstalk:managedactions`]' \
  --output table --region us-east-1
```

## Opt 6 — .ebextensions audit commands (from SKILL.md)

```bash
# List all .ebextensions files
ls -la .ebextensions/

# Check each file for unused resources
for f in .ebextensions/*.config; do
  echo "=== $f ==="
  grep -E "Resources:|files:|packages:|services:|commands:" "$f"
done

# Common issues:
# - Resources created for testing but never removed
# - Duplicate files: blocks across multiple config files
# - Commands that are no longer needed
# - Packages installed but not used by the application
```

## Opt 7 — read current auto-scaling config (from SKILL.md)

```bash
aws elasticbeanstalk describe-configuration-settings \
  --environment-name my-env \
  --query 'ConfigurationSettings[0].OptionSettings[?Namespace==`aws:autoscaling:asg` || Namespace==`aws:autoscaling:trigger`]' \
  --output table --region us-east-1
```

## Opt 8 — verify instance public IP command (from SKILL.md)

```bash
# Check if the instance has a public IP
aws ec2 describe-instances \
  --filters Name=tag:elasticbeanstalk:environment-name,Values=my-dev-env \
  --query 'Reservations[*].Instances[*].{PublicIp:PublicIpAddress,SubnetId:SubnetId}' \
  --output table --region us-east-1
```

## Opt 10 — read current health check config (from SKILL.md)

```bash
aws elasticbeanstalk describe-configuration-settings \
  --environment-name my-env \
  --query 'ConfigurationSettings[0].OptionSettings[?Namespace==`aws:elasticbeanstalk:healthreporting:system`]' \
  --output table --region us-east-1
```

## Opt 11 — check termination protection command (from SKILL.md)

```bash
aws elasticbeanstalk describe-environments \
  --environment-names my-dev-env \
  --query 'Environments[0].{Name:EnvironmentName,TerminationProtected:TerminationProtected}' \
  --output table --region us-east-1
```
