# Baseline (no-skill) response: runtime-eks-process-anomaly

This file captures what a generic assistant produces WITHOUT the
guardduty-finding-investigator skill loaded — the contrast that proves
the skill adds structure (deterministic VERDICT, layer identification,
evidence-backed root cause, finding-type-driven probe order).

---

You have a malicious process running in your EKS pod. The xmrig process
is a crypto miner. You should delete the pod and Kubernetes will
restart it from the clean image.

Then check your other pods and clusters to make sure this hasn't
spread. You may also want to scan the ECR image just to be safe.
