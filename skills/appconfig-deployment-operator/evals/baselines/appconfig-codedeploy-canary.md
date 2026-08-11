# Baseline (no-skill) response: appconfig-codedeploy-canary

This file captures what a generic assistant produces WITHOUT the
appconfig-deployment-operator skill loaded.

---

To create a CodeDeploy deployment group with AppConfig, you can
use:

```
aws deploy create-deployment-group \
  --application-name payments-codedeploy \
  --deployment-group-name payments-dg-prod \
  --service-role-arn arn:aws:iam::111122223333:role/codedeploy-role \
  --deployment-config-name AppConfig.50Percent
```

This should give you a 2-step canary. Make sure your service role
has the right permissions for both CodeDeploy and AppConfig.
