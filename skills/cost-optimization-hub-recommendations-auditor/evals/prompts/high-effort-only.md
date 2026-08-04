# Eval prompt: high-effort-only

Audit the following Cost Optimization Hub configuration for optimization
posture. Emit the standard VERDICT block (ACCOUNT, VERDICT, REASON, FINDINGS,
REMEDIATION).

Account: 111111111111 (management account, Organization with 10 member accounts)

Cost Optimization Hub configuration snapshot:
  enrolled: true
  enrollmentTimestamp: "2024-11-01T00:00:00Z"
  preferences:
    savingsEstimationMode: AFTER_DISCOUNTS
    memberOfServiceLevelOrganization: false
  organizationContext: MANAGEMENT
  orgMemberAccountCount: 10
  memberAccountsVisible: 8
  recommendations:
    - resourceId: "i-0prodapp01"
      resourceType: "AWS::EC2::Instance"
      actionType: "Rightsize"
      effortLevel: "High"
      estimatedSavings: 400.00
      recommendationAgeInDays: 30
      status: "not actioned"
    - resourceId: "i-0prodapp02"
      resourceType: "AWS::EC2::Instance"
      actionType: "Rightsize"
      effortLevel: "High"
      estimatedSavings: 350.00
      recommendationAgeInDays: 25
      status: "not actioned"
    - resourceId: "db-prod-cluster01"
      resourceType: "AWS::RDS::DBInstance"
      actionType: "Migrate"
      effortLevel: "High"
      estimatedSavings: 280.00
      recommendationAgeInDays: 18
      status: "not actioned"
    - resourceId: "lambda-batch-processor"
      resourceType: "AWS::Lambda::Function"
      actionType: "Modify"
      effortLevel: "High"
      estimatedSavings: 150.00
      recommendationAgeInDays: 12
      status: "not actioned"
  totalEstimatedMonthlySavings: 1180.00
