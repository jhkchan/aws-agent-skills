# Eval: multi-document-step-association

**Difficulty:** medium
**Branch:** OPERATION_COMPLETED — custom step-document with two sequential mainSteps, default version set, association pinned to default version, tag:Role=web targets

## Prompt

Create an SSM State Manager association named
ProvisionWebFleet in us-east-1. Use a custom step document
Custom-WebFleetProvision that runs two steps in sequence:
installPackage (yum install -y httpd) then configureService
(systemctl enable and start httpd). Document is at
./custom-webfleet-provision.yaml. Set the document default
version. Target instances tagged Role=web. Schedule
cron(0 0 4 ? * MON-FRI *) (04:00 UTC Mon-Fri). Apply at creation.
Integer rate control: max-concurrency=5, max-errors=2. Output to
s3://my-ssm-output/ssm-output/ (SSE-KMS enabled).
