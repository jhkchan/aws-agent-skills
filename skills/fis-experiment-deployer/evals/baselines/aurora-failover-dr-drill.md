# Baseline (no-skill) — aurora-failover-dr-drill

> This is the response a model produces **without** the skill definition.
> It creates the Aurora failover template but does not verify the
> cluster is in AVAILABLE state, omits the stop-condition alarm state
> check, and grants rds:FailoverDBCluster on Resource: "*". Generated
> for with-skill-vs-baseline comparison.

---

To set up the Aurora failover FIS experiment:

```bash
aws fis create-experiment-template \
  --description "Aurora failover DR drill" \
  --role-arn arn:aws:iam::111111111111:role/FISRole \
  --targets '{"Clusters":{"resourceType":"aws.rds.cluster","resourceArns":["arn:aws:rds:us-east-1:111111111111:cluster:api-prod-cluster"]}}' \
  --actions '{"failover":{"actionId":"aws:rds:failover-db-cluster","targets":{"Clusters":"Clusters"}}}' \
  --stop-conditions '[{"source":"aws:cloudwatch:alarm","value":"arn:aws:cloudwatch:us-east-1:111111111111:alarm:fis-stop-db-connections-dropped"}]' \
  --budget-duration PT5M
```

Add rds:FailoverDBCluster to your FIS role's policy.
