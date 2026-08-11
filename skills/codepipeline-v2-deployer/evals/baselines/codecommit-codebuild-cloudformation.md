# Baseline (no-skill) response: codecommit-codebuild-cloudformation

This file captures what a generic assistant produces WITHOUT the
codepipeline-v2-deployer skill loaded — the contrast that proves the
skill adds structure (deterministic VERDICT, V2 trigger filter
scoping, namespace variable contract, IAM role scope without
wildcards, KMS-encrypted artifact bucket).

---

Here's a plan for your CodePipeline.

Architecture:

- V2 pipeline in us-east-1
- Source: CodeCommit my-service on main
- Build: CodeBuild my-service-build
- Deploy: CloudFormation prod-my-service
- Trigger: on push to main

Steps:

1. Create the pipeline.
2. Configure CodeCommit source.
3. Configure CodeBuild build.
4. Configure CloudFormation deploy.
5. Set up the trigger.

For V2, you need a trigger block since polling is not supported. Add
a branch filter to scope to main.

Commands:

```
aws codepipeline create-pipeline --cli-input-json file://pipeline.json
```

Make sure your IAM role has CodeBuild and CloudFormation permissions.
