# Worked Examples — Elastic Beanstalk Deployer

Full command sequences moved verbatim from SKILL.md. Loaded on demand; each section cites its origin step.

## Step 5 — managed platform update window command (from SKILL.md)

```bash
aws elasticbeanstalk update-environment \
  --environment-name myapp-env \
  --option-settings \
    Namespace=aws:elasticbeanstalk:managedactions:platformaction,OptionName=UpdateLevel,Value=minor \
    Namespace=aws:elasticbeanstalk:managedactions,OptionName=ManagedActionsEnabled,Value=true \
    Namespace=aws:elasticbeanstalk:managedactions,OptionName=PreferredStartTime,Value=Mon:02:00
```

## Step 6 — enhanced health reporting command (from SKILL.md)

```bash
aws elasticbeanstalk update-environment \
  --environment-name myapp-env \
  --option-settings \
    Namespace=aws:elasticbeanstalk:healthreporting:system,OptionName=SystemType,Value=enhanced
```

## Step 9 — VPC-mode create-environment command (from SKILL.md)

```bash
aws elasticbeanstalk create-environment \
  --application-name myapp \
  --environment-name myapp-env \
  --solution-stack-name "64bit Amazon Linux 2023 v6.0.4 running Node.js 20" \
  --option-settings \
    Namespace=aws:ec2:vpc,OptionName=VPCId,Value=vpc-aaa11122 \
    Namespace=aws:ec2:vpc,OptionName=Subnets,Value=subnet-aaa,subnet-bbb \
    Namespace=aws:ec2:vpc,OptionName=ELBSubnets,Value=subnet-aaa,subnet-bbb \
    Namespace=aws:autoscaling:launchconfiguration,OptionName=SecurityGroups,Value=sg-app
```

## Step 10 — auto scaling group config command (from SKILL.md)

```bash
aws elasticbeanstalk update-environment \
  --environment-name myapp-env \
  --option-settings \
    Namespace=aws:autoscaling:asg,OptionName=MinSize,Value=2 \
    Namespace=aws:autoscaling:asg,OptionName=MaxSize,Value=8 \
    Namespace=aws:autoscaling:trigger,OptionName=MeasureName,Value=CPUUtilization \
    Namespace=aws:autoscaling:trigger,OptionName=LowerThreshold,Value=20 \
    Namespace=aws:autoscaling:trigger,OptionName=UpperThreshold,Value=80
```

## Step 13 — CNAME swap blue-green command sequence (from SKILL.md)

```bash
# Deploy green environment (new version)
aws elasticbeanstalk create-environment \
  --application-name myapp --environment-name myapp-green \
  --cname-prefix myapp-green --version-label v2 \
  --template-name myapp-prod-template

# Wait for green to be Ready + Green health
aws elasticbeanstalk describe-environments \
  --environment-names myapp-green \
  --query 'Environments[0].{Status:Status,Health:Health}'

# Swap CNAMEs (atomic DNS cutover)
aws elasticbeanstalk swap-environment-cnames \
  --source-environment-id s-xxxx --destination-environment-id d-yyyy

# Monitor green traffic; if rollback needed, swap back.
# Terminate blue after monitoring period.
```

## Step 14 — application version lifecycle commands (from SKILL.md)

```bash
# Create a new version
aws elasticbeanstalk create-application-version \
  --application-name myapp --version-label v3 \
  --source-bundle S3Bucket=my-bucket,S3Key=app-v3.zip

# Apply a lifecycle policy (keep max 200, delete older)
aws elasticbeanstalk update-application \
  --application-name myapp \
  --resource-lifecycle-config '{"VersionLifecycleConfig":{"MaxCountRule":{"Enabled":true,"MaxCount":200,"DeleteSourceFromS3":true}}}'
```
