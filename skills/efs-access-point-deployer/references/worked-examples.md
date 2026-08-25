# Worked Examples (load on demand) — EFS Access Points Deployer

Secondary example output, moved verbatim from SKILL.md. The primary example (READY_TO_DEPLOY) stays in SKILL.md.

---

## Perfect example output — PREREQUISITES_MISSING (moved from SKILL.md)

```text
ACCESS_POINT: team-a-ap
VERDICT: PREREQUISITES_MISSING
CHECKLIST:
  [✓] File-system baseline: fs-abc123def, Encrypted=true
  [✗] Mount targets in every compute AZ: us-west-2b has no mount target — create one in subnet-2 before proceeding
  [✗] amazon-efs-utils: cannot verify until target host is selected
  [✓] Access point created: team-a-ap (root: /data/team-a, uid: 1000, gid: 1000)
  [✗] File-system policy: not yet applied — mount target gap blocks the deploy
  [✗] Mount via AP alias: blocked pending mount target
  [OPTIONAL] (ECS/EKS) Integration: not requested
  [OPTIONAL] (Lambda) Function VPC + AP: not requested
  [✓] Intelligent-Tiering lifecycle: TransitionTo IA after 30 days
VERIFICATION_COMMANDS:
  aws efs describe-mount-targets --file-system-id fs-abc123def
  aws ec2 describe-subnets --subnet-ids subnet-2 --query 'Subnets[0].[AvailabilityZone,SubnetId]'
```

