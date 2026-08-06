# Eval prompt: stale-high-value-unactioned

Audit the following Cost Optimization Hub configuration for optimization
posture. Emit the standard VERDICT block (ACCOUNT, VERDICT, REASON, FINDINGS,
REMEDIATION).

Account: 111111111111 (management account, Organization with 12 member accounts)

Cost Optimization Hub configuration snapshot:
  enrolled: true
  enrollmentTimestamp: "2024-06-01T00:00:00Z"
  preferences:
    savingsEstimationMode: AFTER_DISCOUNTS
    memberOfServiceLevelOrganization: false
  organizationContext: MANAGEMENT
  orgMemberAccountCount: 12
  memberAccountsVisible: 10
  recommendations:
    - resourceId: "i-0prodapp01"
      resourceType: "AWS::EC2::Instance"
      actionType: "Rightsize"
      effortLevel: "Low"
      estimatedSavings: 850.00
      recommendationAgeInDays: 95
      status: "not actioned"
    - resourceId: "i-0devtest01"
      resourceType: "AWS::EC2::Instance"
      actionType: "Terminate"
      effortLevel: "Low"
      estimatedSavings: 620.00
      recommendationAgeInDays: 112
      status: "not actioned"
    - resourceId: "i-0staging01"
      resourceType: "AWS::EC2::Instance"
      actionType: "Rightsize"
      effortLevel: "Medium"
      estimatedSavings: 180.00
      recommendationAgeInDays: 20
      status: "not actioned"
  totalEstimatedMonthlySavings: 1650.00
