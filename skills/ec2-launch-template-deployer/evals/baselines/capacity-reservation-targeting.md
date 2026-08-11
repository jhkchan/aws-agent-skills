# Baseline (no-skill) — capacity-reservation-targeting

> This is the response a model produces **without** the skill
> definition. It creates the launch template but does not include
> the CapacityReservationSpecification (the instance will launch as
> On-Demand without consuming the reservation), does not verify the
> reservation matches the instance type and AZ, and omits IMDSv2.
> Generated for with-skill-vs-baseline comparison.

---

To create a launch template for a c7i.large in us-east-1:

```bash
aws ec2 create-launch-template \
  --launch-template-name targeted-reservation-web \
  --launch-template-data '{
    "ImageId": "ami-0xyz789",
    "InstanceType": "c7i.large",
    "KeyName": "prod-key",
    "SecurityGroupIds": ["sg-0resv123"]
  }'
```

You mentioned a capacity reservation — you can attach it later in
the console or at launch time if needed.
