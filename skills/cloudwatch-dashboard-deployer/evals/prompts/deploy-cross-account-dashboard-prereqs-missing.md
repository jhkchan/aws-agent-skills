# Eval prompt: deploy-cross-account-dashboard-prereqs-missing

Plan the following CloudWatch dashboard creation and emit the standard
VERDICT block (DASHBOARD, VERDICT, TARGET, PRE_CHECKS, STEPS,
POST_VERIFY, WIDGETS, SHARING, NOTES).

Operation: create
Dashboard name: cross-account-ec2-ops
Region: us-east-1
Account: 111111111111 (monitoring/sharing account)
Cross-account: true
Source accounts:
  - 222222222222 (dev)
  - 333333333333 (staging)
Widgets:
  - type: metric
    title: Dev Account CPU
    namespace: AWS/EC2
    metric: CPUUtilization
    account_id: 222222222222
    dimensions: InstanceId=i-0123456789abcdef0
    statistic: Average
    period: 300
    position: x=0, y=0, w=12, h=6
  - type: metric
    title: Staging Account CPU
    namespace: AWS/EC2
    metric: CPUUtilization
    account_id: 333333333333
    dimensions: InstanceId=i-0abcdef1234567890
    statistic: Average
    period: 300
    position: x=12, y=0, w=12, h=6

```json
{
  "CrossAccountRoleChecks": {
    "iam.get-role.CloudWatch-CrossAccountSharingRole.222222222222": {
      "status": "OK",
      "trustPolicyAllows": "111111111111"
    },
    "iam.get-role.CloudWatch-CrossAccountSharingRole.333333333333": {
      "status": "NoSuchEntity",
      "reason": "Role does not exist in staging account"
    }
  },
  "MetricChecks": {
    "get-metric-statistics.AWS/EC2.CPUUtilization.InstanceId=i-0123456789abcdef0.AccountId=222222222222": {
      "datapoints": 60,
      "Average": 38.2
    },
    "get-metric-statistics.AWS/EC2.CPUUtilization.InstanceId=i-0abcdef1234567890.AccountId=333333333333": {
      "datapoints": 0,
      "reason": "Sharing role missing — metrics not visible from monitoring account"
    }
  },
  "ExistingDashboard": null
}
```
