# Eval prompt: terraform-plan-drift-check

Design a Terraform-based drift detection pipeline using terraform plan
-detailed-exitcode in GitHub Actions. Emit the standard DRIFT_AUTOMATION
block. Include the GitHub Actions workflow YAML and the plan exit-code
logic.

Design reference: terraform-plan-drift-check
IaC tool: Terraform (not CloudFormation)
Pipeline: GitHub Actions
Schedule: daily at 02:00 UTC
S3 bucket for reports: drift-reports
SNS topic: arn:aws:sns:us-east-1:111111111111:terraform-drift-alerts
