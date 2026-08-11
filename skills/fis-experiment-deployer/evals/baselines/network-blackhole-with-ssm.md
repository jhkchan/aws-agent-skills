# Baseline (no-skill) — network-blackhole-with-ssm

> This is the response a model produces **without** the skill definition.
> It builds the SSM-based blackhole but does not verify SSM agent
> connectivity, omits the manual rollback runbook, and does not cite
> that network actions persist if SSM is unreachable at action end.
> Generated for with-skill-vs-baseline comparison.

---

Use SSM Run Command from FIS to add an iptables rule:

```bash
aws fis create-experiment-template \
  --description "Network blackhole app to DB" \
  --role-arn arn:aws:iam::111111111111:role/FISRole \
  --targets '{"Instances":{"resourceType":"aws.ec2.instance","resourceArns":["arn:aws:ec2:us-east-1:111111111111:instance/i-0abc456"]}}' \
  --actions '{"blackhole":{"actionId":"aws:ssm:start-automation-execution","parameters":{"documentArn":"AWS-RunShellScript","documentParameters":"{\"commands\":[\"iptables -I INPUT -s 10.0.0.20 -j DROP\"]}","duration":"PT5M"},"targets":{"Instances":"Instances"}}}' \
  --stop-conditions '[{"source":"aws:cloudwatch:alarm","value":"arn:aws:cloudwatch:us-east-1:111111111111:alarm:fis-stop-api-latency"}]' \
  --budget-duration PT10M
```

The iptables rule will block traffic to the DB.
