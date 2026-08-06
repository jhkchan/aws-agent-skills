# Eval prompt: clean-production-config

Audit the following Cost Optimization Hub configuration for optimization
posture. Emit the standard VERDICT block (ACCOUNT, VERDICT, REASON, FINDINGS,
REMEDIATION).

Account: 111111111111 (management account, Organization with 6 member accounts)

Cost Optimization Hub configuration snapshot:
  enrolled: true
  enrollmentTimestamp: "2024-03-01T00:00:00Z"
  preferences:
    savingsEstimationMode: AFTER_DISCOUNTS
    memberOfServiceLevelOrganization: false
  organizationContext: MANAGEMENT
  orgMemberAccountCount: 6
  memberAccountsVisible: 6
  recommendations:
    - resourceId: "i-0appserver01"
      resourceType: "AWS::EC2::Instance"
      actionType: "Rightsize"
      effortLevel: "Low"
      estimatedSavings: 120.00
      recommendationAgeInDays: 8
      status: "not actioned"
    - resourceId: "i-0appserver02"
      resourceType: "AWS::EC2::Instance"
      actionType: "Rightsize"
      effortLevel: "Medium"
      estimatedSavings: 95.00
      recommendationAgeInDays: 5
      status: "not actioned"
    - resourceId: "lambda-data-processor"
      resourceType: "AWS::Lambda::Function"
      actionType: "Modify"
      effortLevel: "High"
      estimatedSavings: 80.00
      recommendationAgeInDays: 3
      status: "not actioned"
  totalEstimatedMonthlySavings: 295.00
