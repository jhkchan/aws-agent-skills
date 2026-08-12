# Baseline (no-skill) response: stackset-multi-account

This file captures what a generic assistant produces WITHOUT the
ssm-patch-compliance-automator skill loaded.

---

For multi-account patching, you can use CloudFormation StackSets to
deploy the patch baseline across all your member accounts. Create a
template with an AWS::SSM::PatchBaseline resource and deploy it to
your Organization OU.

```
aws cloudformation create-stack-set --stack-set-name "patch-baseline" --template-body file://baseline.yaml ...
aws cloudformation create-stack-instances --stack-set-name "patch-baseline" --deployment-targets OrganizationalUnitIds=["ou-abc-123defghi"] ...
```

Once the baseline is deployed to each account, you'll need to tag the
instances with the patch group and register the baseline. You can do
this through the SSM console or CLI in each account.

For automation, you could write a Lambda function that iterates
through your accounts and registers the patch baseline for the patch
group in each one.
