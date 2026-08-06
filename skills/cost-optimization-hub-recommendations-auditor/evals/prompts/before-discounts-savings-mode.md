# Eval prompt: before-discounts-savings-mode

Audit the following Cost Optimization Hub configuration for optimization
posture. Emit the standard VERDICT block (ACCOUNT, VERDICT, REASON, FINDINGS,
REMEDIATION).

Account: 111111111111 (management account, Organization with 8 member accounts)

Cost Optimization Hub configuration snapshot:
  enrolled: true
  enrollmentTimestamp: "2024-09-01T00:00:00Z"
  preferences:
    savingsEstimationMode: BEFORE_DISCOUNTS
    memberOfServiceLevelOrganization: false
  organizationContext: MANAGEMENT
  orgMemberAccountCount: 8
  memberAccountsVisible: 8
  recommendations:
    - resourceId: "i-0webserver01"
      resourceType: "AWS::EC2::Instance"
      actionType: "Rightsize"
      effortLevel: "Low"
      estimatedSavings: 210.00
      recommendationAgeInDays: 15
      status: "not actioned"
    - resourceId: "i-0webserver02"
      resourceType: "AWS::EC2::Instance"
      actionType: "Rightsize"
      effortLevel: "Medium"
      estimatedSavings: 180.00
      recommendationAgeInDays: 10
      status: "not actioned"
  totalEstimatedMonthlySavings: 390.00
