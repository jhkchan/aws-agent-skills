# Baseline (no-skill) — private-app-sam-deploy

> This is the response a model produces **without** the skill
> definition. It mentions publishing the app but misses the SAM
> transform-before-CFN pipeline, the application policy requirement
> for cross-account deploy (consumer 999999999999 gets 403 without
> it), the CAPABILITY_IAM requirement (transform auto-generates IAM
> roles), and the READY_TO_DEPLOY checklist format. Generated for
> with-skill-vs-baseline comparison.

---

You can publish the app using the AWS CLI:

```bash
aws serverlessrepo create-application \
  --author "Jacky Chan" \
  --description "S3 file processor" \
  --semantic-version "1.0.0" \
  --template-body file://template.yaml
```

Then the other account can deploy it.
