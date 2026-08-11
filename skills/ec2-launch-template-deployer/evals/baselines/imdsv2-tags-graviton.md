# Baseline (no-skill) — imdsv2-tags-graviton

> This is the response a model produces **without** the skill
> definition. It creates a launch template with the right AMI and
> instance type but omits the IMDSv2 `HttpTokens=required` setting
> (leaves the instance vulnerable to SSRF-driven IMDSv1 credential
> theft), forgets the hop-limit tuning for containers, uses gp2
> instead of gp3 for the block devices, and does not emit the
> READY_TO_DEPLOY checklist format. Generated for with-skill-vs-
> baseline comparison.

---

Here's a launch template for your Graviton web server:

```bash
aws ec2 create-launch-template \
  --launch-template-name graviton-web-server \
  --launch-template-data '{
    "ImageId": "ami-0abcdef1234567890",
    "InstanceType": "m7g.large",
    "KeyName": "prod-graviton-key",
    "SecurityGroupIds": ["sg-0abc123", "sg-0def456"],
    "IamInstanceProfile": { "Arn": "arn:aws:iam::123456789012:instance-profile/web-server-role" },
    "BlockDeviceMappings": [{
      "DeviceName": "/dev/xvda",
      "Ebs": { "VolumeSize": 30 }
    }]
  }'
```

That should cover it. The instance will have the Graviton processor
and the right AMI.
