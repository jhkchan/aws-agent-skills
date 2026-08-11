# Baseline (no-skill) — eks-pod-disruption

> This is the response a model produces **without** the skill definition.
> It builds the EKS pod-disruption template via SSM kubectl but does
> not verify SSM agent connectivity, does not cite kubeconfig/EKS API
> permission requirements, and does not document the silent-failure
> mode where SSM succeeds but kubectl has no permissions. Generated
> for with-skill-vs-baseline comparison.

---

Use SSM Run Command to invoke kubectl on the EKS worker node:

```bash
aws fis create-experiment-template \
  --description "EKS pod kill for api" \
  --role-arn arn:aws:iam::111111111111:role/FISRole \
  --targets '{"Instances":{"resourceType":"aws.ec2.instance","resourceArns":["arn:aws:ec2:us-east-1:111111111111:instance/i-0abc789"]}}' \
  --actions '{"podkill":{"actionId":"aws:ssm:start-automation-execution","parameters":{"documentArn":"AWS-RunShellScript","documentParameters":"{\"commands\":[\"kubectl delete pod -n api -l app=critical --grace-period=0 --force\"]}"},"targets":{"Instances":"Instances"}}}' \
  --stop-conditions '[{"source":"aws:cloudwatch:alarm","value":"arn:aws:cloudwatch:us-east-1:111111111111:alarm:fis-stop-api-5xx"}]' \
  --budget-duration PT3M
```

Add ssm:SendCommand to the FIS role.
