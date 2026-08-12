# Eval prompt: ecr-image-scan-rebuild

Design an Inspector v2 automation workflow for the following
ECR container finding. Emit the standard FINDING block (SEVERITY,
DETECTION, RESPONSE, SSM_RUNBOOK, VERIFICATION, MULTI_ACCOUNT,
VERDICT, TEMPLATE). Include the CodeBuild rebuild trigger and the
scheduled rescan recommendation.

Design reference: ecr-image-scan-rebuild
Account: 111111111111
Region: us-east-1

Finding: CVE-2026-5678 on log4j in base image (CVSS 9.1)
Severity: CRITICAL
Resource: AWS_ECR_CONTAINER_IMAGE prod-app:v1.2.3
CodeBuild project: arn:aws:codebuild:us-east-1:111111111111:project/container-rebuild-pipeline
ECR scan-on-push: enabled on prod-app repo
Existing image has 12 deployed copies in ECS.
Pre-prod validation: completed.
