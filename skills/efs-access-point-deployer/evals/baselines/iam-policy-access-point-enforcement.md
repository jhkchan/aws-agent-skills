# Baseline (no-skill) — iam-policy-access-point-enforcement

> This is the response a model produces **without** the skill definition.
> It includes an `Allow` with the access-point ARN condition but omits
> the explicit `Deny` on `Null:AccessPointArn` — so identity-based IAM
> can still grant a direct mount via the file-system DNS name, silently
> bypassing the access-point-only intent. Generated for with-skill-vs-
> baseline comparison.

---

To create the access point and policy:

1. Create the access point:
```bash
aws efs create-access-point \
  --name prod-app-ap \
  --file-system-id fs-aaaabbbbcccc \
  --posix-user Uid=2000,Gid=2000 \
  --root-directory Path=/app,CreationInfo={OwnerUid=2000,OwnerGid=2000,Permissions=0750}
```

2. Apply the file-system policy:
```bash
aws efs put-file-system-policy --file-system-id fs-aaaabbbbcccc --policy '{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {"AWS": "arn:aws:iam::123456789012:role/AppRole"},
    "Action": [
      "elasticfilesystem:ClientMount",
      "elasticfilesystem:ClientWrite",
      "elasticfilesystem:ClientRootAccess"
    ],
    "Resource": "arn:aws:elasticfilesystem:us-east-1:123456789012:file-system/fs-aaaabbbbcccc",
    "Condition": {
      "StringEquals": {
        "elasticfilesystem:AccessPointArn": "arn:aws:elasticfilesystem:us-east-1:123456789012:access-point/fsap-prod-app"
      }
    }
  }]
}'
```

3. Mount via the access point:
```bash
sudo mount -t efs -o tls,accesspoint=fsap-prod-app fs-aaaabbbbcccc:/ /mnt/efs
```

The access-point-only policy is enforced.
