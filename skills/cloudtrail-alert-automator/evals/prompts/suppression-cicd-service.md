# Eval prompt: suppression-cicd-service

Design a CloudTrail alerting automation with CI/CD service account
suppression. Emit the standard ALERT block (RULE, ENRICHMENT, ROUTING,
DEDUP, SUPPRESSION, VERDICT, TEMPLATE).

Design reference: suppression-cicd-service
Account: 111111111111
Region: us-east-1

CloudTrail: management-events trail, multi-region, enabled.
Events: UpdateStack, CreateChangeSet (from CI/CD pipeline).
Known automation roles to suppress:
  - arn:aws:sts::111111111111:assumed-role/cicd-deploy-role
  - arn:aws:sts::111111111111:assumed-role/AWSCloudFormationStackSetExecutionRole
  - arn:aws:iam::111111111111:role/aws-service-role/autoscaling.amazonaws.com/AWSServiceRoleForAutoScaling
Dedup window: 30 minutes for stack updates.
Audit: all suppressed events must be logged.
Non-suppressible events: DeleteTrail, StopLogging, root.
