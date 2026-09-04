# Security skills (52)

Precise call: `@skills:gh:jhkchan/aws-agent-skills/skills/<name>` (swap `<name>` for a row below).

| Skill | Task type | What it does |
|---|---|---|
| `accessanalyzer-finding-triage` | audit | Triages IAM Access Analyzer findings (external access + unused access) into risk verdicts with remediation. |
| `acm-certificate-deployer` | deploy | Provisions AWS ACM certificates with production defaults: certificate request (domain names, wildcard), DNS validation (Route53 CNAME, cross-account), |
| `acm-certificate-expiry-auditor` | audit | Audits AWS Certificate Manager (ACM) certificates for expiry risk, renewal health, validation method, and key-algorithm strength. |
| `acm-certificate-monitor-operator` | operate | Operates AWS ACM certificate monitoring and expiry tracking with production defaults: DaysToExpiry CloudWatch alarm creation (threshold <30 days warni |
| `acm-private-ca-deployer` | deploy | Provisions AWS Private Certificate Authority (ACM PCA) with production defaults: CA creation (root vs subordinate), key algorithm (RSA_2048, EC_prime2 |
| `certificate-renewal-automator` | automate | Designs and implements ACM certificate renewal automation pipelines. |
| `cloudhsm-cluster-deployer` | deploy | Provisions AWS CloudHSM clusters with production defaults: cluster creation in a VPC with subnets across 2+ AZs for HA, HSM instance creation, one-tim |
| `cloudhsm-cluster-posture-auditor` | audit | Audits AWS CloudHSM clusters for high-availability posture (HSM count and cross-AZ distribution), backup/restore readiness (retention policy, backup r |
| `cognito-auth-troubleshooter` | troubleshoot | Diagnoses Amazon Cognito authentication failures through a twelve-category diagnostic tree: User Pool sign-in errors (wrong app client, wrong auth flo |
| `cognito-identity-pool-deployer` | deploy | Provisions Amazon Cognito Identity Pools (federated identities) with production defaults: identity pool creation, identity providers (Cognito User Poo |
| `cognito-idp-user-pool-auditor` | audit | Audits Amazon Cognito user pools for security posture — MFA enforcement, password policy strength, app-client auth-flow safety (SRP vs password vs adm |
| `cognito-user-pool-deployer` | deploy | Provisions Amazon Cognito user pools with secure defaults — user pool attributes (standard and custom), password policy, MFA (SMS/TOTP), app clients ( |
| `detective-investigation-coverage-auditor` | audit | Audits Amazon Detective behavior graph coverage, member-account ingestion health, data-source package states (DETECTIVE_CORE, EKS_AUDIT, EKS_RUNTIME), |
| `directory-service-deployer` | deploy | Provisions AWS Directory Service with production defaults: directory type selection (Managed Microsoft AD, Simple AD, AD Connector), edition sizing (S |
| `ec2-security-group-auditor` | audit | Classifies each EC2 security group's inbound exposure as OPEN, PUBLIC_NONCRITICAL, or RESTRICTED (worst-case per-rule aggregation) and emits remediati |
| `firewall-manager-compliance-auditor` | audit | Audits AWS Firewall Manager (FMS) policies across WAF, Shield Advanced, VPC Security Groups, Network Firewall, DNS Firewall, and third-party firewalls |
| `firewall-manager-deployer` | deploy | Provisions AWS Firewall Manager (FMS) policies with production defaults: policy creation (WAF, Security Group, Network Firewall, Shield Advanced), man |
| `guardduty-finding-automator` | automate | Designs and implements automated response workflows for Amazon GuardDuty findings. |
| `guardduty-finding-investigator` | troubleshoot | Investigates Amazon GuardDuty findings through a finding-type-driven diagnostic tree covering Recon:IAMUser, UnauthorizedAccess:EC2, Backdoor:EC2, Cry |
| `guardduty-finding-severity-triage` | audit | Classifies Amazon GuardDuty findings into a context-aware triage severity (CRITICAL | HIGH | MEDIUM | LOW | LIKELY_FALSE_POSITIVE) by overlaying findi |
| `iam-key-rotation-automator` | automate | Designs and implements IAM access key rotation automation pipelines. |
| `iam-least-privilege-advisor` | audit | Analyzes AWS IAM policies to identify over-permissive grants — wildcard actions, wildcard resources, privilege-escalation actions (PassRole, AssumeRol |
| `iam-permission-troubleshooter` | troubleshoot | Diagnoses AWS IAM AccessDenied, ExplicitDeny, Client.UnauthorizedOperation, and NotAuthorized sts:AssumeRole errors via a systematic policy-evaluation |
| `iam-role-deployer` | deploy | Creates production-grade IAM roles with correct trust policies and least- privilege permissions across all principal types: AWS service roles (lambda, |
| `incident-response-automator` | automate | Designs automated AWS incident response workflows across detection (GuardDuty, Security Hub, CloudWatch alarms, EventBridge, AWS Health) and response  |
| `inspector2-automation-automator` | automate | Designs and deploys Amazon Inspector v2 automation workflows — enabling Inspector across EC2, ECR, and Lambda resources; EventBridge routing for findi |
| `inspector2-coverage-finding-auditor` | audit | Audits Amazon Inspector2 coverage gaps and finding severity to determine whether EC2 instances, ECR repositories, and Lambda functions are effectively |
| `inspector2-coverage-operator` | operate | Operates Amazon Inspector v2 coverage across an AWS Organization or single account — enables / disables Inspector per account and region, manages EC2  |
| `inspector2-finding-troubleshooter` | troubleshoot | Diagnoses Amazon Inspector v2 vulnerability findings through a finding-type-driven diagnostic tree covering network reachability (unreachable ports, u |
| `kms-key-deployer` | deploy | Provisions AWS KMS keys correctly: key type selection (symmetric AES-256, asymmetric RSA/ECDSA, HMAC), key spec, key policy with separated key adminis |
| `kms-key-policy-auditor` | audit | Audits AWS KMS key policies and key metadata for cross-account or external principals, wildcard kms:* grants, the kms:Decrypt blast-radius multiplier, |
| `kms-key-rotation-operator` | operate | Operates AWS KMS key rotation workflows end-to-end — key type classification (AWS-managed, customer-managed symmetric, asymmetric RSA/ECDSA, HMAC, Mul |
| `kms-key-rotation-optimizer` | optimize | Optimises AWS KMS key rotation and lifecycle cost across seven dimensions: key inventory audit (orphaned keys at $1/key/month, unused key detection vi |
| `macie-cost-optimizer` | optimize | Optimises Amazon Macie cost across seven dimensions: discovery mode selection (automated data discovery vs one-off targeted classification jobs — auto |
| `macie-data-classification-auditor` | audit | Audits Amazon Macie data-classification posture — classification job coverage and status, automated sensitive data discovery (ASDD) enablement, sensit |
| `macie-data-discovery-operator` | operate | Operates Amazon Macie data discovery lifecycle — enables Macie (org-level delegated admin), creates classification jobs (one-time vs scheduled, S3 sco |
| `network-firewall-rule-auditor` | audit | Audits AWS Network Firewall configurations for permissive stateful and stateless rules, missing TLS inspection, firewall-subnet routing gaps that bypa |
| `rolesanywhere-trust-deployer` | deploy | Provisions IAM Roles Anywhere trust infrastructure with production defaults: trust anchor creation (binding an external certificate authority to AWS I |
| `secrets-manager-rotation-troubleshooter` | troubleshoot | Diagnoses AWS Secrets Manager rotation failures through a ten-category diagnostic tree: rotation Lambda errors at the database (wrong host, port, data |
| `secrets-rotation-operator` | operate | Operates AWS Secrets Manager rotation workflows end-to-end — rotation Lambda setup (Python template + IAM), rotation configuration (Lambda ARN, cron s |
| `secretsmanager-rotation-auditor` | audit | Audits AWS Secrets Manager secrets for rotation posture — rotation enablement, rotation-Lambda health (existence, execution-role permissions, VPC conn |
| `securityhub-control-compliance-auditor` | audit | Audits AWS Security Hub control compliance findings and maps each to a deterministic compliance verdict (FAILED | WARNING | PASSED | NOT_APPLICABLE),  |
| `securityhub-finding-troubleshooter` | troubleshoot | Diagnoses and resolves AWS Security Hub findings through a standard-driven decision tree covering CIS AWS Foundations Benchmark, PCI DSS 3.2.1, AWS Fo |
| `securityhub-remediation-automator` | automate | Designs automated remediation workflows for AWS Security Hub findings using EventBridge rules, SSM Automation runbooks, and Lambda remediation functio |
| `shield-advanced-coverage-auditor` | audit | Audits AWS Shield Advanced coverage posture — protected-resource coverage (CloudFront/Route 53 auto-protection, ALB/NLB/CLB/EIP/EC2 explicit protectio |
| `signer-signing-profile-deployer` | deploy | Provisions AWS Signer signing profiles with production defaults: platform selection (AWSLambda-SHA384-ECDSA, AmazonFreeRTOS, AWSIoT) where the platfor |
| `sts-cross-account-role-auditor` | audit | Audits IAM role trust policies (AssumeRolePolicyDocument) for cross-account exposure, wildcard Principal grants, confused-deputy service-principal vec |
| `verified-permissions-policy-auditor` | audit | Audits Amazon Verified Permissions policy stores for Cedar policy validation, schema-to-policy consistency, principal/resource authorization scope, po |
| `vpc-lattice-auth-auditor` | audit | Audits VPC Lattice service networks for auth-policy absence (default-open posture), public Principal:"*" Invoke grants, NotAction inverse-wildcard tra |
| `waf-rule-deployer` | deploy | Provisions AWS WAFv2 rule sets with production defaults: Web ACL creation (CloudFront scope in us-east-1 vs Regional scope), rule groups (managed vs c |
| `wafv2-web-acl-auditor` | audit | Audits AWS WAFv2 Web ACL configurations to determine whether the ACL provides effective protection: default-action posture (Allow vs Block), managed-r |
| `wafv2-web-acl-deployer` | deploy | Provisions AWS WAFv2 Web ACLs with correct production defaults: scope selection (CLOUDFRONT vs REGIONAL), managed rule groups (AWSManagedRulesCommonRu |
