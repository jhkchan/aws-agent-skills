# Diagnostic Commands (load on demand) — EC2 Instance Rightsizer

CLI listings for family migration, Graviton AMI lookup and launch, burstable credit mode, Spot price history, and the pre-flight safety checks, moved verbatim from SKILL.md.


---

## Step 3 — Migration method (same architecture) (moved from SKILL.md)

**Migration method (same architecture):**
```bash
# 1. Stop the instance
aws ec2 stop-instances --instance-ids i-0abc123def456

# 2. Change the instance type
aws ec2 modify-instance-attribute --instance-id i-0abc123def456 \
  --instance-type "{\"Value\": \"m6i.large\"}"

# 3. Start the instance
aws ec2 start-instances --instance-ids i-0abc123def456

# 4. Verify
aws ec2 describe-instances --instance-ids i-0abc123def456 \
  --query 'Reservations[0].Instances[0].InstanceType'
```

## Step 4 — arm64 AMI lookup and Graviton launch procedure (moved from SKILL.md)

**AMI requirement:**
```bash
# Find an arm64 AMI
aws ec2 describe-images \
  --owners amazon \
  --filters "Name=architecture,Values=arm64" \
            "Name=name,Values=al2023-ami-*" \
  --query 'sort_by(Images, &CreationDate)[-1].ImageId' \
  --output text
```

**Graviton migration is always a new-instance launch, NOT a modify:**
```bash
# 1. Launch a new Graviton instance from an arm64 AMI
aws ec2 run-instances \
  --image-id ami-0newarm64ami \
  --instance-type m7g.large \
  --key-name my-key \
  --security-group-ids sg-0abc123 \
  --subnet-id subnet-0abc123 \
  --tag-specifications "ResourceType=instance,Tags=[{Key=Name,Value=web-server-arm64-test}]"

# 2. Deploy and test the application on arm64
# 3. Verify all dependencies work (native libs, DB drivers, ML models)
# 4. Cut over DNS or load balancer to the new instance
# 5. Decommission the old x86 instance
```

## Step 5 — Enable/disable Unlimited mode (moved from SKILL.md)

**Enable/disable Unlimited:**
```bash
# Enable Unlimited mode
aws ec2 modify-instance-credit-specification \
  --instance-credit-specifications \
    InstanceId=i-0abc123def456,CpuCredits=unlimited

# Revert to standard
aws ec2 modify-instance-credit-specification \
  --instance-credit-specifications \
    InstanceId=i-0abc123def456,CpuCredits=standard
```

## Step 8 — Spot price history lookup (moved from SKILL.md)

Spot pricing varies by AZ and time. Always check current Spot rates:
```bash
aws ec2 describe-spot-price-history \
  --instance-types m6i.large \
  --availability-zones us-east-1a \
  --product-descriptions "Linux/UNIX" \
  --start-time $(date -d '-1 day' +%FT%TZ) \
  --end-time $(date +%FT%TZ)
```

## Pre-flight safety checks (run before any remediation CLI) (moved from SKILL.md)

- **MANDATORY CONFIRMATION GATE.** Before any state-changing operation
  (stop, start, modify-instance-attribute, terminate), emit and await
  operator approval. Do NOT execute until confirmed.
- **Check termination protection before stop/terminate.** An instance
  with `disableApiTermination = true` requires explicit unblocking
  first. Surface it as a gate.
- **Take an AMI snapshot before cross-family migration.** Production
  instances should have a rollback AMI before modifying the type.
- **Verify Graviton compatibility before launch.** Test on a staging
  arm64 instance before cutting over production.
- **Stop before modify-instance-attribute.** Instance type changes
  require the instance to be stopped.
- **Monitor for 7 days post-change.** CPU, memory, and application-
  level metrics should be within expected ranges after right-sizing.
- **Bulk-operation limit:** Process at most 5 instances per batch.
  Sort by estimated savings, verify each batch before proceeding.
  Abort if any instance shows increased errors or degraded performance
  post-change.
