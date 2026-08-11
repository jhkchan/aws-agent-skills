# Baseline (no-skill) — ec2-stop-canary-with-alarm

> This is the response a model produces **without** the skill definition.
> It creates the experiment template but scopes ec2:StopInstances to
> Resource: "*" without tag conditions, omits the S3 bucket policy
> grant, and does not cite alarm state. Generated for with-skill-vs-
> baseline comparison.

---

To create the FIS experiment:

```bash
aws fis create-experiment-template \
  --description "Stop canary EC2 for 60s" \
  --role-arn arn:aws:iam::111111111111:role/FISRole \
  --targets '{"Instances":{"resourceType":"aws.ec2.instance","resourceTags":{"fis-target":"true"}}}' \
  --actions '{"stop":{"actionId":"aws:ec2:stop-instances","parameters":{"duration":"PT60S"},"targets":{"Instances":"Instances"}}}' \
  --stop-conditions '[{"source":"aws:cloudwatch:alarm","value":"arn:aws:cloudwatch:us-east-1:111111111111:alarm:fis-stop-error-rate"}]' \
  --budget-duration PT2M
```

Make sure your FIS role has ec2:StopInstances and ec2:StartInstances.
