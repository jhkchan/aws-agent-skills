# Baseline (no-skill) response: kms-and-imdsv-gaps

This file captures what a generic assistant produces WITHOUT the
eks-security-optimizer skill loaded — the contrast that proves the skill
adds structure (deterministic VERDICT, severity scoring, KMS re-encryption
warning, IMDSv2 hop-limit explanation, CONFIRM gate).

---

Your cluster has good pod-level security with PSA, IRSA on all
namespaces, Cilium network policies, and Istio mTLS. However there are
two infrastructure-level gaps:

1. No KMS secrets encryption — your Kubernetes secrets are using the
default encryption instead of a customer-managed KMS key. You should
enable KMS encryption:

```
aws kms create-key --description "EKS secrets encryption"
aws eks update-cluster-config --name kms-and-imdsv-gaps \
  --encryption-config '{"resources":["secrets"],"provider":{"keyArn":"..."}}'
```

Note that existing secrets won't be automatically re-encrypted, so you'll
need to rotate them after enabling KMS.

2. IMDSv2 not enforced — your nodes have HttpPutResponseHopLimit=2 which
means pods can reach the Instance Metadata Service. This allows credential
theft via SSRF. You should set hop-limit to 1 and require IMDSv2:

```
aws ec2 modify-instance-metadata-options --instance-id <id> \
  --http-tokens required --http-put-response-hop-limit 1
```

These are both important security improvements. The IMDSv2 issue is
probably more urgent since it directly enables credential theft.
