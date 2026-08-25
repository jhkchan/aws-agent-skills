# EC2 Security-Group Auditor — diagnostic commands (moved from SKILL.md)

Loaded on demand — content moved verbatim from SKILL.md (progressive disclosure; nothing deleted).

### Effective enumeration queries

The single most useful query for scoping an audit — find every SG in
the region that allows a given CIDR (the `ip-permission.cidr` filter
matches on substring, so use the exact value):

```
aws ec2 describe-security-groups \
  --filters Name=ip-permission.cidr,Values=0.0.0.0/0 \
            Name=ip-permission.from-port,Values=22 \
  --query 'SecurityGroups[*].[GroupId,GroupName,VpcId]' --output table
```

For IPv6 exposure, repeat with `Name=ip-permission.ipv6-ranges.cidr,Values=::/0`.
