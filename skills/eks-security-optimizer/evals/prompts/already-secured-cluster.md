# Eval prompt: already-secured-cluster

Assess the security posture of the following EKS cluster. Walk all
security dimensions (pod security, IAM identity, network policies,
secrets encryption, image scanning, runtime security, admission
policies, mTLS) and emit the standard security optimization block
(TARGET, VERDICT, REASON, RECOMMENDATION, SEVERITY, ESTIMATED_RISK,
REMEDIATION_STEPS).

ClusterName: already-secured-cluster
Region: us-east-1
KubernetesVersion: 1.30

Pod Security Admission: restricted-enforce on all non-system namespaces
IRSA: enabled on all non-system namespaces (20/20)
Network Policies: Calico installed, default-deny in all namespaces
  with explicit allow rules for all required flows
Secrets Encryption: KMS enabled (customer-managed key, rotation enabled)
ECR Image Scanning: scan-on-push enabled with enhanced scanning
  (Inspector), CRITICAL findings block policy via Kyverno
GuardDuty EKS Runtime: enabled (aws-guardduty-agent active)
Admission Webhook: Kyverno deployed (15 policies including
  disallow-privileged, require-resource-limits, verify-image-scans)
Service Mesh mTLS: Istio installed with STRICT mTLS mode
Audit Logging: all 5 types enabled (api, audit, authenticator,
  controllerManager, scheduler)
API Server Endpoint: private only (accessed via VPN)
IMDSv2: enforced (HttpPutResponseHopLimit=1)
