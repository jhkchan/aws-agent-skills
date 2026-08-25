# EC2 Spot Fleet Deployer — diagnostic commands (moved from SKILL.md)

Loaded on demand — content moved verbatim from SKILL.md (progressive disclosure; nothing deleted).
## Step 8 — Spot placement score: query and sample output (moved from SKILL.md)
**Query Spot placement scores:**
```bash
aws ec2 get-spot-placement-scores \
  --instance-types m5.large m5a.large c5.large \
  --target-capacity 10 \
  --target-capacity-type vcpu \
  --region us-east-1 \
  --single-availability-zone true
```

**Output:**
```json
{
  "SpotPlacementScores": [
    { "Region": "us-east-1", "AvailabilityZoneId": "use1-az1", "Score": 10 },
    { "Region": "us-east-1", "AvailabilityZoneId": "use1-az2", "Score": 7 },
    { "Region": "us-east-1", "AvailabilityZoneId": "use1-az3", "Score": 3 }
  ]
}
```
