# Diagnostic Commands (load on demand) — Directory Service Deployer

VPC/subnet/DNS verification commands and snapshot/restore commands moved verbatim from SKILL.md.
The prerequisites table and step decision logic remain in SKILL.md.

---

## Step 3 — VPC and subnet placement verification commands (moved from SKILL.md)

```bash
# Verify subnets exist and are in different AZs
aws ec2 describe-subnets \
  --filters Name=vpc-id,Values=vpc-aaa11122 \
  --query 'Subnets[*].{SubnetId:SubnetId,AZ:AvailabilityZone,CIDR:CidrBlock}' \
  --region us-east-1 --output table

# Verify VPC DNS support
aws ec2 describe-vpc-attribute --vpc-id vpc-aaa11122 \
  --attribute enableDnsSupport --region us-east-1

# Enable if needed
aws ec2 modify-vpc-attribute --vpc-id vpc-aaa11122 \
  --enable-dns-support --region us-east-1
aws ec2 modify-vpc-attribute --vpc-id vpc-aaa11122 \
  --enable-dns-hostnames --region us-east-1
```

---

## Step 11 — Snapshot and restore commands (moved from SKILL.md)

```bash
# Create a manual snapshot
aws ds create-snapshot \
  --directory-id d-aaa111222 \
  --name "pre-change-snapshot" \
  --region us-east-1

# Restore from a snapshot (full overwrite, 1-2 hours)
aws ds restore-from-snapshot \
  --snapshot-id s-xxx \
  --region us-east-1

# List snapshots
aws ds describe-snapshots \
  --directory-id d-aaa111222 \
  --region us-east-1 --output table
```
