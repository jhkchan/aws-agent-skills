# Eval prompt: ebs-volume-optimized

Audit the following Compute Optimizer finding for the EBS volume. Emit the
standard VERDICT block (RESOURCE, VERDICT, REASON, RISK, FINDINGS, REMEDIATION).

Resource type: EBS volume
Volume ARN: arn:aws:ec2:us-east-1:111111111111:volume/vol-ebs-volume-optimized
Current configuration: { volumeType: gp3, volumeSizeGB: 100, baselineIOPS: 3000, baselineThroughputMBps: 125 }
Finding: Optimized
Finding reasons: []
Utilization metrics:
  - name: VolumeReadOpsPerSecond, statistic: Average, value: 1500.0
  - name: VolumeWriteOpsPerSecond, statistic: Average, value: 800.0
  - name: VolumeReadBytesPerSecond, statistic: Average, value: 25.0
  - name: VolumeWriteBytesPerSecond, statistic: Average, value: 15.0
Recommendation options: []
Last refresh timestamp: 2026-07-29
