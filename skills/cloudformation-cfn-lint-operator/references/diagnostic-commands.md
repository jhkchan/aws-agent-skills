# Diagnostic Commands — CloudFormation cfn-lint Operator

Load-on-demand command listings moved verbatim from SKILL.md.

## Step 11 — Rollback template archive (archive and rollback commands)

```bash
# Archive the current template to versioned S3
aws cloudformation get-template --stack-name my-stack \
  --query 'TemplateBody' --region us-east-1 > "template-$(date +%Y%m%d%H%M%S).yaml"
aws s3 cp "template-$(date +%Y%m%d%H%M%S).yaml" s3://my-cfn-archive/templates/ --region us-east-1

# To roll back: deploy the archived template
aws cloudformation update-stack --stack-name my-stack \
  --template-body file://template-previous.yaml --region us-east-1
```
