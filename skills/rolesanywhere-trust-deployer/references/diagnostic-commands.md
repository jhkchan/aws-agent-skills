# Diagnostic Commands — Roles Anywhere Trust Deployer

Pre-flight and post-deployment verification commands moved out of the SKILL.md body. Loaded on demand.


## Verify the temporary credentials work (Step 6)

```bash
# Use the credentials to list S3 buckets
AWS_PROFILE=rolesanywhere aws s3 ls

# Or export the credentials manually
eval "$(./aws_signing_helper credential-process \
  --certificate client-cert.pem \
  --private-key client-key.pem \
  --trust-anchor-id "$TRUST_ANCHOR_ID" \
  --profile-id "$PROFILE_ID" \
  --role-arn arn:aws:iam::123456789012:role/RolesAnywhereCIRunner \
  --region us-east-1 --output env)"

aws sts get-caller-identity
```


## Query CloudTrail for Roles Anywhere sessions (Step 8)

```bash
aws cloudtrail lookup-events \
  --lookup-attributes "AttributeKey=EventName,AttributeValue=AssumeRoot" \
  --start-time "$(date -u -v-1H +%Y-%m-%dT%H:%M:%SZ)" \
  --end-time "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
  --region us-east-1 \
  --query 'Events[*].{Time:EventTime,User:Username,Role:EventName}' \
  --output table
```
