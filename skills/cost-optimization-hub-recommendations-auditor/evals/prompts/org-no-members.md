# Eval prompt: org-no-members

Audit the following Cost Optimization Hub configuration for optimization
posture. Emit the standard VERDICT block (ACCOUNT, VERDICT, REASON, FINDINGS,
REMEDIATION).

Account: 111111111111 (management account, Organization with 20 member accounts)

Cost Optimization Hub configuration snapshot:
  enrolled: true
  enrollmentTimestamp: "2025-06-01T00:00:00Z"
  preferences:
    savingsEstimationMode: AFTER_DISCOUNTS
    memberOfServiceLevelOrganization: false
  organizationContext: MANAGEMENT
  orgMemberAccountCount: 20
  memberAccountsVisible: 0
  recommendations:
    - resourceId: "i-0mgmtserver01"
      resourceType: "AWS::EC2::Instance"
      actionType: "Rightsize"
      effortLevel: "Low"
      estimatedSavings: 120.00
      recommendationAgeInDays: 14
      status: "not actioned"
  totalEstimatedMonthlySavings: 120.00
