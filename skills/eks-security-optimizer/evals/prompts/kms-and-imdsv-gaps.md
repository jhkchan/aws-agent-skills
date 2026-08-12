# Eval prompt: kms-and-imdsv-gaps

Assess the security posture of the following EKS cluster. Walk all
security dimensions (pod security, IAM identity, network policies,
secrets encryption, image scanning, runtime security, admission
policies, mTLS) and emit the standard security optimization block
(TARGET, VERDICT, REASON, RECOMMENDATION, SEVERITY, ESTIMATED_RISK,
REMEDIATION_STEPS).

ClusterName: kms-and-imdsv-gaps
Region: us-east-1
KubernetesVersion: 1.30

Pod Security Admission: baseline-enforce on all non-system namespaces,
  restricted-audit on production
IRSA: enabled on all non-system namespaces (15/15)
Network Policies: Cilium installed, default-deny in all namespaces
  with explicit allow rules
Secrets Encryption: KMS NOT configured (uses default encryption)
ECR Image Scanning: scan-on-push enabled with enhanced scanning
GuardDuty EKS Runtime: enabled
Admission Webhook: Gatekeeper deployed (8 policies enforced)
Service Mesh mTLS: Istio installed with STRICT mTLS mode
Audit Logging: all 5 types enabled
API Server Endpoint: public with restricted CIDR ranges
IMDSv2: NOT enforced (HttpPutResponseHopLimit=2, IMDSv1 accessible)
