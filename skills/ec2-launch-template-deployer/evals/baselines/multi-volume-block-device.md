# Baseline (no-skill) — multi-volume-block-device

> This is the response a model produces **without** the skill
> definition. It specifies only the root volume with default gp2
> type and no IOPS tuning, omits the data volume entirely, does not
> map the instance store ephemeral device, and sets
> DeleteOnTermination to false on non-root volumes (the default),
> which leads to orphaned-volume cost accumulation. Generated for
> with-skill-vs-baseline comparison.

---

Here's a launch template for the data-processing worker:

```bash
aws ec2 create-launch-template \
  --launch-template-name data-worker \
  --launch-template-data '{
    "ImageId": "ami-0dataworker",
    "InstanceType": "m5d.large",
    "KeyName": "data-key",
    "SecurityGroupIds": ["sg-0data"],
    "BlockDeviceMappings": [{
      "DeviceName": "/dev/xvda",
      "Ebs": { "VolumeSize": 50 }
    }]
  }'
```

The m5d.large has instance store NVMe disks so you don't need to
worry about EBS for scratch space.
