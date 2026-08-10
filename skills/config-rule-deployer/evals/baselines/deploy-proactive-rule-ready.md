# Baseline (no-skill) response: deploy-proactive-rule-ready

This file captures what a generic assistant produces WITHOUT the
config-rule-deployer skill loaded.

---

To deploy a proactive Config rule using CloudFormation hooks, you need
to register a hook type and create a stack:

```bash
aws cloudformation register-type \
  --type-name CfnHook::Config::ProactiveRule \
  --type-resource-type HOOK \
  --schema-handler-package s3://my-bucket/proactive-rule-hook.zip
```

Then create a stack with the hook resource to block non-compliant
S3 bucket creation.
