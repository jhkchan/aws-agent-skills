# Baseline (no-skill) — ebs-csi-irsa

> This is the response a model produces **without** the skill
> definition. It mentions the EBS CSI add-on but misses the correct
> service account name (ebs-csi-controller-sa), the IRSA trust policy
> specifics, the IAM policy details, and the READY_TO_DEPLOY checklist.

---

Install the EBS CSI driver:

```bash
aws eks create-addon --cluster-name app-cluster \
  --addon-name aws-ebs-csi-driver \
  --service-account-role-arn arn:aws:iam::123456789012:role/EBSRole
```

Create the role with EBS permissions and attach it.
