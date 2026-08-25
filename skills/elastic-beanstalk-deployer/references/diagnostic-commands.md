# Diagnostic Commands — Elastic Beanstalk Deployer

Pre-flight and verification commands moved verbatim from SKILL.md. Loaded on demand.

## IAM pre-flight verification commands (from SKILL.md § Step 8)

```bash
# Verify service role exists
aws iam get-role --role-name aws-elasticbeanstalk-service-role

# Verify instance profile exists with correct role
aws iam get-instance-profile --instance-profile-name aws-elasticbeanstalk-ec2-role
```
