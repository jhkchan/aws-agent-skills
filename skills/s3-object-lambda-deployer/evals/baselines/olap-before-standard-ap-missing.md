# Baseline (no-skill) response: olap-before-standard-ap-missing

This file captures what a generic assistant produces WITHOUT the
s3-object-lambda-deployer skill loaded. The contrast proves the skill
catches the OLAP-before-standard-AP prerequisite (routing breaks if
the standard AP does not exist) — the baseline provisions without
verifying.

---

Sure, you can create the OLAP first and set up the standard AP later.
Here are the commands:

```bash
aws s3control create-access-point-for-object-lambda \
  --account-id 111111111111 --name new-olap \
  --configuration SupportingAccessPoint=arn:aws:s3:us-east-1:111111111111:accesspoint/reports-ap

aws s3control put-access-point-configuration-for-object-lambda \
  --account-id 111111111111 --name new-olap \
  --configuration '{"TransformationConfigurations":[{"Actions":["GetObject"],"ContentTransformation":{"AwsLambda":{"FunctionArn":"arn:aws:lambda:us-east-1:111111111111:function:reports-redact-fn"}}}]}'
```

Then when you're ready, create the standard AP:

```bash
aws s3control create-access-point --account-id 111111111111 --name reports-ap --bucket shared-reports
```

The OLAP will start working once the standard AP is in place.
