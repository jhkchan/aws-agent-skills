# Eval prompt: network-policy-gap

Assess the security posture of the following EKS cluster. Walk all
security dimensions (pod security, IAM identity, network policies,
secrets encryption, image scanning, runtime security, admission
policies, mTLS) and emit the standard security optimization block
(TARGET, VERDICT, REASON, RECOMMENDATION, SEVERITY, ESTIMATED_RISK,
REMEDIATION_STEPS).

ClusterName: network-policy-gap
Region: us-east-1
KubernetesVersion: 1.30

Pod Security Admission: restricted-enforce on production namespaces,
  baseline-enforce on all others
IRSA: enabled on all non-system namespaces (18/18)
Network Policies: none (no Calico or Cilium installed, default allow)
Secrets Encryption: KMS enabled
ECR Image Scanning: scan-on-push enabled with enhanced scanning
GuardDuty EKS Runtime: enabled
Admission Webhook: OPA Gatekeeper deployed (10 policies enforced)
Service Mesh mTLS: App Mesh with permissive mode (not strict)
Audit Logging: all 5 types enabled
API Server Endpoint: private only
IMDSv2: enforced (HttpPutResponseHopLimit=1)
