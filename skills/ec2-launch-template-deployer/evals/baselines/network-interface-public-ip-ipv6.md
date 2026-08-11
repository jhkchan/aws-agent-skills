# Baseline (no-skill) — network-interface-public-ip-ipv6

> This is the response a model produces **without** the skill
> definition. It uses the top-level SecurityGroupIds (which is
> silently overridden if NetworkInterfaces is also present), does
> not set AssociatePublicIpAddress inside NetworkInterfaces on
> DeviceIndex 0, and omits Ipv6AddressCount entirely. The resulting
> instance may not get a public IP or IPv6. Generated for with-
> skill-vs-baseline comparison.

---

For a public-facing API server on c7i.xlarge:

```bash
aws ec2 create-launch-template \
  --launch-template-name api-server \
  --launch-template-data '{
    "ImageId": "ami-0apiimage",
    "InstanceType": "c7i.xlarge",
    "KeyName": "api-key",
    "SecurityGroupIds": ["sg-0api"],
    "SubnetId": "subnet-0public",
    "BlockDeviceMappings": [{
      "DeviceName": "/dev/xvda",
      "Ebs": { "VolumeSize": 30 }
    }]
  }'
```

If you need a public IP, you can allocate an Elastic IP and attach
it after launch.
