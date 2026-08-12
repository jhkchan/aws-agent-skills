# Baseline (no-skill) response: instance-type-downgrade-further-optimization

This file captures what a generic assistant produces WITHOUT the
apprunner-autoscaling-optimizer skill loaded.

---

Your service is on 2 vCPU / 4 GB but only using 15% CPU and 22% memory.
You could downgrade to a smaller instance type to save money. Update the
service configuration:

```bash
aws apprunner update-service \
  --service-arn <arn> \
  --instance-configuration '{"Cpu": "1 vCPU", "Memory": "2 GB"}'
```

This should roughly halve your per-instance cost. Make sure to test the
service after the change to verify performance is still acceptable.
