# Baseline (no-skill) response: graviton-migration

This file captures what a generic assistant produces WITHOUT the
ec2-instance-rightsizer skill loaded — the contrast that proves the
skill adds structure (deterministic VERDICT, Graviton AMI + application
compatibility verification, dollar savings math, CONFIRM gate).

---

Your m5.xlarge instance could potentially benefit from migrating to
AWS Graviton (ARM64) processors. Graviton instances are generally
cheaper than their x86 counterparts.

Since you're running Python and Node.js, both of which support ARM64,
this should work. The m7g.xlarge would be a good equivalent to your
current m5.xlarge.

You can migrate by launching a new instance with an ARM64 AMI and then
moving your workload over. Something like:

```
aws ec2 run-instances --image-id ami-0arm64ami --instance-type m7g.xlarge --key-name my-key --security-group-ids sg-xxx --subnet-id subnet-xxx
```

Then once you've tested everything works, you can decommission the old
instance. Graviton instances are about 15-20% cheaper so with your
current usage you should see some savings.
