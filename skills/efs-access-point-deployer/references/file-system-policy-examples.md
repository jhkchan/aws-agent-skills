# File-System Policy Examples — EFS Access Points Deployer

Reference policy templates for the IAM file-system policy, the
access-point-only enforcement `Deny`, the ECS task role, the EKS CSI
driver IRSA role, and the Lambda execution role. Substitute
`<FS_ID>`, `<AP_ID>`, `<ACCOUNT>`, `<REGION>`, `<APP_ROLE>`,
`<EKS_ROLE>`, `<LAMBDA_ROLE>`, `<UID>`, `<GID>`, `<PREFIX>` as
needed. Stored here so the main skill body stays scannable; see the
9-step procedure for when to apply each variant.

## 1. File-system policy — access-point-only enforcement

The `Deny` is what closes the DNS-name bypass. Without it, identity-
based IAM can still grant direct mount via
`fs-<id>.efs.<region>.amazonaws.com`, defeating "access-point-only."

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "AllowThroughAccessPoint",
      "Effect": "Allow",
      "Principal": { "AWS": "arn:aws:iam::<ACCOUNT>:role/<APP_ROLE>" },
      "Action": [
        "elasticfilesystem:ClientMount",
        "elasticfilesystem:ClientWrite",
        "elasticfilesystem:ClientRootAccess"
      ],
      "Resource": "arn:aws:elasticfilesystem:<REGION>:<ACCOUNT>:file-system/<FS_ID>",
      "Condition": {
        "StringEquals": {
          "elasticfilesystem:AccessPointArn": "arn:aws:elasticfilesystem:<REGION>:<ACCOUNT>:access-point/<AP_ID>"
        }
      }
    },
    {
      "Sid": "DenyNonAccessPointMounts",
      "Effect": "Deny",
      "Principal": "*",
      "Action": "elasticfilesystem:ClientMount",
      "Resource": "arn:aws:elasticfilesystem:<REGION>:<ACCOUNT>:file-system/<FS_ID>",
      "Condition": {
        "Null": { "elasticfilesystem:AccessPointArn": "true" }
      }
    }
  ]
}
```

The `Null: { elasticfilesystem:AccessPointArn: "true" }` condition
reads: "Deny if the AccessPointArn key is absent." Mounts via the AP
alias set the key; mounts via the FS DNS name do not.

## 2. File-system policy — read-only analytics consumer

For a consumer that should mount read-only (e.g., a metrics scraper),
drop `ClientWrite` and `ClientRootAccess`:

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Sid": "ReadOnlyThroughAccessPoint",
    "Effect": "Allow",
    "Principal": { "AWS": "arn:aws:iam::<ACCOUNT>:role/AnalyticsReadRole" },
    "Action": ["elasticfilesystem:ClientMount"],
    "Resource": "arn:aws:elasticfilesystem:<REGION>:<ACCOUNT>:file-system/<FS_ID>",
    "Condition": {
      "StringEquals": {
        "elasticfilesystem:AccessPointArn": "arn:aws:elasticfilesystem:<REGION>:<ACCOUNT>:access-point/<AP_ID>"
      }
    }
  }]
}
```

Without `ClientWrite`, writes fail at the NFS layer with `EACCES`,
not at mount time — operators see a successful mount followed by
write errors.

## 3. ECS task execution role inline policy

The ECS task role needs ClientMount + ClientWrite +
ClientRootAccess. Without `ClientRootAccess`, the AP's directory
permissions are silently ignored.

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Sid": "EFSMountViaAccessPoint",
    "Effect": "Allow",
    "Action": [
      "elasticfilesystem:ClientMount",
      "elasticfilesystem:ClientWrite",
      "elasticfilesystem:ClientRootAccess"
    ],
    "Resource": "arn:aws:elasticfilesystem:<REGION>:<ACCOUNT>:file-system/<FS_ID>",
    "Condition": {
      "StringEquals": {
        "elasticfilesystem:AccessPointArn": "arn:aws:elasticfilesystem:<REGION>:<ACCOUNT>:access-point/<AP_ID>"
      }
    }
  }]
}
```

The ECS volume config sets `iam: ENABLED` so the mount uses the task
role credentials; without it, the mount falls back to the EC2
instance profile or fails.

## 4. EKS CSI driver IRSA role policy

The CSI driver dynamically creates access points per PVC. Its IRSA
role needs full AP lifecycle + ClientRootAccess for the AP's
directory permissions to take effect.

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "ManageAccessPoints",
      "Effect": "Allow",
      "Action": [
        "elasticfilesystem:CreateAccessPoint",
        "elasticfilesystem:DeleteAccessPoint",
        "elasticfilesystem:DescribeAccessPoints",
        "elasticfilesystem:DescribeFileSystems",
        "elasticfilesystem:DescribeMountTargets",
        "elasticfilesystem:CreateMountTarget",
        "elasticfilesystem:TagResource"
      ],
      "Resource": "*"
    },
    {
      "Sid": "ClientAccess",
      "Effect": "Allow",
      "Action": [
        "elasticfilesystem:ClientMount",
        "elasticfilesystem:ClientWrite",
        "elasticfilesystem:ClientRootAccess"
      ],
      "Resource": "arn:aws:elasticfilesystem:<REGION>:<ACCOUNT>:file-system/<FS_ID>"
    }
  ]
}
```

The trust policy MUST reference the EKS OIDC provider with the
`efs-csi-controller-sa` service account:

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {
      "Federated": "arn:aws:iam::<ACCOUNT>:oidc-provider/<OIDC_PROVIDER>"
    },
    "Action": "sts:AssumeRoleWithWebIdentity",
    "Condition": {
      "StringEquals": {
        "<OIDC_PROVIDER>:sub": "system:serviceaccount:kube-system:efs-csi-controller-sa"
      }
    }
  }]
}
```

## 5. Lambda execution role policy

Lambda mounts EFS via the function's execution role. Same actions
as the ECS task role; without `ClientRootAccess`, the AP's POSIX
identity override silently fails.

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Sid": "LambdaEFSMount",
    "Effect": "Allow",
    "Action": [
      "elasticfilesystem:ClientMount",
      "elasticfilesystem:ClientWrite",
      "elasticfilesystem:ClientRootAccess"
    ],
    "Resource": "arn:aws:elasticfilesystem:<REGION>:<ACCOUNT>:file-system/<FS_ID>"
  }]
}
```

The Lambda function also needs `ec2:CreateNetworkInterface`,
`ec2:DescribeNetworkInterfaces`, and `ec2:DeleteNetworkInterface`
for VPC attachment — these come from the `AWSLambdaVPCAccessExecutionRole`
managed policy.

## 6. Cross-account EFS access

To grant a foreign account's role access to an EFS file system:

```json
{
  "Sid": "CrossAccountAccess",
  "Effect": "Allow",
  "Principal": { "AWS": "arn:aws:iam::<FOREIGN_ACCOUNT>:role/<FOREIGN_ROLE>" },
  "Action": [
    "elasticfilesystem:ClientMount",
    "elasticfilesystem:ClientWrite"
  ],
  "Resource": "arn:aws:elasticfilesystem:<REGION>:<ACCOUNT>:file-system/<FS_ID>"
}
```

The foreign client still needs network reachability (VPC peering or
Transit Gateway) to the mount target's subnet. Without network
reachability, the mount hangs at the TCP level; no IAM error is
returned.
