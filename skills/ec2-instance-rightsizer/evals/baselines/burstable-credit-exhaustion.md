# Baseline (no-skill) response: burstable-credit-exhaustion

This file captures what a generic assistant produces WITHOUT the
ec2-instance-rightsizer skill loaded — the contrast that proves the
skill adds structure (deterministic VERDICT, credit exhaustion analysis,
Unlimited vs m-family cost comparison, CONFIRM gate).

---

Your t3.large instance is running out of CPU credits, with the balance
dropping from 144 to 12 over the last 14 days. That means the instance
is being throttled to baseline performance during builds.

For a CI/CD runner that has sustained high CPU usage, you might want
to either enable Unlimited mode or switch to a non-burstable instance
type. Unlimited mode lets you borrow credits but charges extra. Or you
could move to an m6i.large which gives consistent CPU without worrying
about credits.

To enable Unlimited:

```
aws ec2 modify-instance-credit-specification --instance-credit-specifications InstanceId=i-burstable-credit-exhaustion,CpuCredits=unlimited
```

Or to change the instance type:

```
aws ec2 stop-instances --instance-ids i-burstable-credit-exhaustion
aws ec2 modify-instance-attribute --instance-id i-burstable-credit-exhaustion --instance-type "{\"Value\": \"m6i.large\"}"
aws ec2 start-instances --instance-ids i-burstable-credit-exhaustion
```

Either option should help with your build performance.
