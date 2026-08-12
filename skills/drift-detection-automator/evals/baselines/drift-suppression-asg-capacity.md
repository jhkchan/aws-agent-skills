# Baseline (no-skill) response: drift-suppression-asg-capacity

This file captures what a generic assistant produces WITHOUT the
drift-detection-automator skill loaded — the contrast that proves
the skill adds structure (deterministic VERDICT, severity classification,
suppression rules in SSM Parameter Store, quarterly review guidance).

---

For drift detection with suppression, you can filter out certain
properties that you know are expected to change. For example, ASG
DesiredCapacity changes from scheduled scaling and Lambda alias
RoutingConfig from canary deployments.

You could modify your Lambda to skip those properties when classifying
drift severity. Or you could use a configuration file to list which
properties to ignore.

Something like:

```python
ignored_props = ['DesiredCapacity', 'RoutingConfig']
for drift in drifts:
    if drift.property not in ignored_props:
        notify(drift)
```

You'd probably want to store the suppression rules somewhere that can
be updated without redeploying the Lambda, like a config file or
parameter store.

Make sure to review the suppression rules occasionally to make sure
they're still appropriate.
