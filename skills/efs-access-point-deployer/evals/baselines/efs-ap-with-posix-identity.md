# Baseline (no-skill) — efs-ap-with-posix-identity

> This is the response a model produces **without** the skill definition.
> It creates the access point but omits the file-system policy's
> `Null:AccessPointArn` Deny (so the policy is dead text on direct
> mounts), uses `mount -t nfs4 -o tls` instead of `mount -t efs`
> (so TLS is silently ignored), and skips the Intelligent-Tiering
> verification. Generated for with-skill-vs-baseline comparison.

---

To create an EFS access point for Team A:

1. Create the access point:
```bash
aws efs create-access-point \
  --name team-a-ap \
  --file-system-id fs-0abc123def \
  --posix-user Uid=1000,Gid=1000 \
  --root-directory Path=/data/team-a
```

2. Mount it on the EC2 instances:
```bash
sudo mount -t nfs4 -o tls,hard fs-0abc123def.efs.us-east-1.amazonaws.com:/ /mnt/efs
```

Team A can now read and write files under /data/team-a through the
access point. The POSIX identity is set, and the directory will be
auto-created.
