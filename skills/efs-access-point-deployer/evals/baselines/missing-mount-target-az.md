# Baseline (no-skill) — missing-mount-target-az

> This is the response a model produces **without** the skill definition.
> It proceeds with access-point creation without flagging the missing
> mount target in us-west-2c, leaving the operator unaware that
> compute in that AZ will silently cross-AZ mount (incurring cost
> and latency). Generated for with-skill-vs-baseline comparison.

---

To create the EFS access point for internal-logs:

1. Create the access point:
```bash
aws efs create-access-point \
  --name internal-logs-ap \
  --file-system-id fs-998877 \
  --posix-user Uid=1001,Gid=1001 \
  --root-directory Path=/logs,CreationInfo={OwnerUid=1001,OwnerGid=1001,Permissions=0750}
```

2. Attach a restrictive file-system policy that requires mounts to
   come through the access point:
```bash
aws efs put-file-system-policy --file-system-id fs-998877 --policy '{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {"AWS": "*"},
    "Action": "elasticfilesystem:ClientMount",
    "Resource": "arn:aws:elasticfilesystem:us-west-2:123456789012:file-system/fs-998877"
  }]
}'
```

3. Mount via the access point from your EC2 hosts:
```bash
sudo mount -t efs -o tls,accesspoint=<AP_ID> fs-998877:/ /mnt/efs
```

The access point is ready and the policy is in place.
