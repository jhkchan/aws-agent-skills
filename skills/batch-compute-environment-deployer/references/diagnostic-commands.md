# Batch Compute Environment Deployer — diagnostic command listings

Content moved verbatim from SKILL.md (progressive disclosure). Load on demand.

---

## Detecting capacity starvation (Step 10 — CloudWatch metrics and scheduling priority) (moved verbatim from SKILL.md)

**Detecting capacity starvation** (the #1 Batch issue):

```bash
# Check for RUNNABLE jobs
aws batch list-jobs --job-queue production-queue --job-status RUNNABLE

# Check compute environment status
aws batch describe-compute-environments --compute-environments batch-ec2-env
```

Common causes of RUNNABLE stuck: job requests more vCPUs than any
instance type provides, instance role trust policy broken, security
group blocks outbound 443, subnet has no available IPs, or maxvCpus too
low.

