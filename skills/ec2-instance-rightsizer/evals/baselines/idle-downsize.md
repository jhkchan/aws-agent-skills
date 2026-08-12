# Baseline (no-skill) response: idle-downsize

This file captures what a generic assistant produces WITHOUT the
ec2-instance-rightsizer skill loaded — the contrast that proves the
skill adds structure (deterministic VERDICT, CWAgent memory citation,
dollar savings estimate, CONFIRM gate, termination protection check).

---

Your m5.2xlarge instance is barely using any CPU at 3.2% average. With
only 28% memory utilization, you could definitely downsize this
instance to save money.

The Compute Optimizer recommends m5.large, which seems reasonable for
a web server that doesn't need much resources. That would cut your
cost significantly.

You can change the instance type with:

```
aws ec2 stop-instances --instance-ids i-idle-downsize
aws ec2 modify-instance-attribute --instance-id i-idle-downsize --instance-type "{\"Value\": \"m5.large\"}"
aws ec2 start-instances --instance-ids i-idle-downsize
```

An m5.2xlarge costs about $0.384/hour while m5.large is $0.096/hour,
so you'd save quite a bit. Make sure to monitor the instance after the
change to make sure it handles the load fine.
