# Diagnostic commands - CodeBuild Build Troubleshooter

> Moved verbatim from SKILL.md for progressive disclosure (agentskills.io). Load on demand.

## Pre-flight: gather-info gate

```bash
# 1. Build details (phases, logs, source, environment, artifacts)
aws codebuild batch-get-builds --ids <build-id> --output json

# 2. Project details (environment, serviceRole, source, vpcConfig, cache)
aws codebuild batch-get-projects --names <project-name> --output json

# 3. Build log events
aws logs get-log-events \
  --log-group-name /aws/codebuild/<project-name> \
  --log-stream-name <stream> --output json

# 4. Service role policy check
ROLE_NAME=$(echo <role-arn> | cut -d/ -f2)
aws iam list-attached-role-policies --role-name <role-name> --output json
aws iam list-role-policies --role-name <role-name> --output json

# 5. AWS Health (regional CodeBuild events)
aws health describe-events \
  --filter eventStatusCodes=OPEN,UPCOMING --output json
```

