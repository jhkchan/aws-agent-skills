# Baseline (no-skill) response: missing-source-config

This file captures what a generic assistant produces WITHOUT the
codepipeline-v2-deployer skill loaded. The contrast proves the skill
enforces the pre-flight specification gate (catches missing source
action and emits PREREQUISITES_MISSING instead of assuming CodeCommit
or producing a partial plan).

---

Here's a plan for your V2 pipeline.

Architecture:

- V2 pipeline in us-east-1
- Build: CodeBuild my-service-build
- Deploy: CloudFormation prod-my-service

Steps:

1. Create the pipeline.
2. Configure CodeBuild.
3. Configure CloudFormation deploy.

You didn't specify the source, so I've assumed CodeCommit on the main
branch. Adjust if you meant S3 or GitHub.

Commands:

```
aws codepipeline create-pipeline --cli-input-json file://pipeline.json
```

Fill in the source action details (repository name, branch) and you
should be good to go.
