# Diagnostic Commands — Cloud9 Environment Deployer

Load-on-demand verification commands moved verbatim from SKILL.md.

## Step 2 — SSM mode requirements (verification commands)

```bash
# Verify the instance profile role has SSM permissions
aws iam list-attached-role-policies \
  --role-name Cloud9InstanceProfile \
  --query 'AttachedPolicies[*].PolicyName' --output text
# Must include AmazonSSMManagedInstanceCore
```

## Step 2 — SSH mode requirements (verification commands)

```bash
# Key pair must exist
aws ec2 describe-key-pairs --key-names my-cloud9-key

# Security group must allow port 22 from trusted CIDR
aws ec2 describe-security-groups \
  --group-ids sg-aaa11122 \
  --query 'SecurityGroups[0].IpPermissions[?FromPort==`22`]'
```
