# Error Handling (load on demand) — Compute Optimizer Findings Auditor

Per-verdict remediation guidance (UNDERUTILIZED / NOT_OPTIMIZED / OK), moved verbatim from SKILL.md.


---

## Remediation guidance (moved from SKILL.md)

### For UNDERUTILIZED (Overprovisioned, HIGH confidence)

**EC2:**
1. Create a pre-rightsize AMI (see Pre-flight).
2. Stop the instance: `aws ec2 stop-instances --instance-ids <id>`.
3. Change type: `aws ec2 modify-instance-attribute --instance-id <id>
   --instance-type "{\"Value\": \"<new-type>\"}"`.
4. Start: `aws ec2 start-instances --instance-ids <id>`.
5. Monitor CloudWatch CPU + Memory for 7 days. If CPU > 80% or Memory >
   85%, roll back to the original type.

**EBS:**
1. `aws ec2 modify-volume --volume-id <id> --volume-type <new-type>
   --size <new-size> --iops <new-iops>`.
2. Verify the modification completes: `aws ec2 describe-volumes-modifications
   --volume-ids <id>`.

**Lambda:**
1. `aws lambda update-function-configuration --function-name <name>
   --memory-size <new-mb>`.
2. Check CloudWatch metrics `Duration` and `Errors` for 1-3 days.
3. If Duration increases or Errors spike, roll back to original memory.

**ASG:**
1. Create a new launch template version with the recommended instance type.
2. Update the ASG to use the new template version.
3. Trigger instance refresh: `aws autoscaling start-instance-refresh
   --auto-scaling-group-name <name>`.
4. Monitor the refresh until complete.

### For NOT_OPTIMIZED

**Underprovisioned (performance risk):**
1. Identify the bottleneck from `findingReasons`
   (CPUUnderprovisioned, MemoryUnderprovisioned, etc.).
2. UP-size the resource to a recommendation option with
   `performanceRisk` ≤ 2.
3. Same EC2/EBS/Lambda CLI steps as UNDERUTILIZED, but with a LARGER type.

**Low confidence (inferred memory / high performanceRisk):**
1. Install CloudWatch Agent for memory metrics (EC2).
2. Wait 30 days for Compute Optimizer to analyse with real data.
3. Re-evaluate. Do NOT act on the current finding.

**Stale finding:**
1. Re-run recommendations: `aws compute-optimizer
   get-ec2-instance-recommendations --instance-arns <arn>`.
2. Check `lastRefreshTimestamp` on the new finding.
3. Re-evaluate with fresh data.

### For OK

1. No remediation required for the current posture.
2. Recommend installing CWAgent if not present (defense-in-depth for future
   findings).
3. Recommend reviewing findings quarterly as workloads evolve.
