# Eval prompt: psa-irsa-network-gaps

Assess the security posture of the following EKS cluster. Walk all
security dimensions (pod security, IAM identity, network policies,
secrets encryption, image scanning, runtime security, admission
policies, mTLS) and emit the standard security optimization block
(TARGET, VERDICT, REASON, RECOMMENDATION, SEVERITY, ESTIMATED_RISK,
REMEDIATION_STEPS).

ClusterName: psa-irsa-network-gaps
Region: us-east-1
KubernetesVersion: 1.30

Pod Security Admission: not configured (no PSS labels on namespaces)
IRSA: enabled on 3 of 15 namespaces (remaining 12 use node IAM role)
Network Policies: none (default allow all east-west traffic)
Secrets Encryption: KMS not configured (uses default encryption)
ECR Image Scanning: scan-on-push enabled (enhanced scanning via Inspector)
GuardDuty EKS Runtime: enabled (aws-guardduty-agent addon active)
Admission Webhook: OPA Gatekeeper deployed (8 policies enforced)
Service Mesh mTLS: not configured (no App Mesh or Istio)
Audit Logging: enabled (api, audit, authenticator, controllerManager, scheduler)
API Server Endpoint: public (0.0.0.0/0) with private endpoint also enabled
IMDSv2: enforced (HttpPutResponseHopLimit=1)
