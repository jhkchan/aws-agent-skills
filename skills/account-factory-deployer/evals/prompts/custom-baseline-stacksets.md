# Eval: custom-baseline-stacksets

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — custom StackSet deployed alongside default Control Tower baseline, VPC customization verified

## Prompt

Vend a new account "ml-platform-prod" via Account Factory with a custom
baseline. Root email aws+prod-ml@company.com. OU "Custom (ML)"
(ou-ml-001). Custom StackSet "CustomBaseline-VPC" deploying a VPC with
public/private subnets. Default Control Tower baseline expected. Assign
MLResearcherAccess to MLTeam group. Management account 123456789012.
Tags: Environment=production.
