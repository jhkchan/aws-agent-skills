# Eval prompt: irsa-migration-opportunity

Assess the security posture of the following EKS cluster. Walk all
security dimensions (pod security, IAM identity, network policies,
secrets encryption, image scanning, runtime security, admission
policies, mTLS) and emit the standard security optimization block
(TARGET, VERDICT, REASON, RECOMMENDATION, SEVERITY, ESTIMATED_RISK,
REMEDIATION_STEPS).

ClusterName: irsa-migration-opportunity
Region: us-east-1
KubernetesVersion: 1.30

Pod Security Admission: baseline-enforce on all non-system namespaces,
  restricted-audit on production namespaces
IRSA: enabled on 4 of 20 namespaces (remaining 16 use node IAM role)
Network Policies: Calico installed, default-deny in all namespaces,
  explicit allow rules configured
Secrets Encryption: KMS enabled (customer-managed key)
ECR Image Scanning: scan-on-push enabled with enhanced scanning
GuardDuty EKS Runtime: enabled
Admission Webhook: Kyverno deployed (12 policies enforced)
Service Mesh mTLS: Istio installed with STRICT mTLS mode
Audit Logging: all 5 types enabled
API Server Endpoint: public with restricted CIDR ranges (10.0.0.0/8)
IMDSv2: enforced (HttpPutResponseHopLimit=1)
