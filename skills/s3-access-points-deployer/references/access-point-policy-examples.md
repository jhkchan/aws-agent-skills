# Access Point Policy Examples — S3 Access Points Deployer

Reference policy templates for access points, the through-AP-only bucket-
policy Deny, the VPC-endpoint policy, cross-account delegation, and the
Object Lambda invocation policy. Substitute `<AP_NAME>`, `<ACCOUNT>`,
`<REGION>`, `<BUCKET>`, `<VPC_ID>`, `<ROLE_ARN>`, `<PREFIX>`, `<FUNC_ARN>`
as needed. Stored here so the main skill body stays scannable; see the
9-step procedure for when to apply each variant.

## 1. Access point policy — per-team prefix-scoped read/write

The Resource MUST be the access-point ARN (`arn:aws:s3:<region>:<account>:accesspoint/<name>`),
not the bucket ARN. Requests through the AP present the AP ARN as the
resource; a policy whose Resource is the bucket ARN matches nothing.

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Sid": "TeamAPrefixReadWrite",
    "Effect": "Allow",
    "Principal": { "AWS": "arn:aws:iam::<ACCOUNT>:role/TeamARole" },
    "Action": [
      "s3:GetObject",
      "s3:PutObject",
      "s3:DeleteObject",
      "s3:ListBucket"
    ],
    "Resource": [
      "arn:aws:s3:<REGION>:<ACCOUNT>:accesspoint/<AP_NAME>",
      "arn:aws:s3:<REGION>:<ACCOUNT>:accesspoint/<AP_NAME>/<PREFIX>/*"
    ]
  }]
}
```

## 2. Access point policy — read-only analytics consumer

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Sid": "AnalyticsReadOnly",
    "Effect": "Allow",
    "Principal": { "AWS": "arn:aws:iam::<ACCOUNT>:role/AthenaReadRole" },
    "Action": [
      "s3:GetObject",
      "s3:GetObjectVersion",
      "s3:ListBucket"
    ],
    "Resource": [
      "arn:aws:s3:<REGION>:<ACCOUNT>:accesspoint/<AP_NAME>",
      "arn:aws:s3:<REGION>:<ACCOUNT>:accesspoint/<AP_NAME>/*"
    ]
  }]
}
```

## 3. Through-AP-only bucket-policy Deny (REQUIRED for VPC-only claim)

This statement, applied to the BUCKET policy, denies any request that
did not come through the named access point. Without this, the bucket's
global hostname remains reachable by any principal with `s3:GetObject`
and the "VPC-only" claim is false.

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Sid": "RequireThroughAccessPoint",
    "Effect": "Deny",
    "Principal": "*",
    "Action": "s3:*",
    "Resource": [
      "arn:aws:s3:::<BUCKET>",
      "arn:aws:s3:::<BUCKET>/*"
    ],
    "Condition": {
      "StringNotEqualsIfExists": {
        "s3:DataAccessPointArn": "arn:aws:s3:<REGION>:<ACCOUNT>:accesspoint/<AP_NAME>"
      },
      "Null": { "aws:SourceVpc": "false" }
    }
  }]
}
```

The condition key MUST be `s3:DataAccessPointArn`. Do NOT substitute
`aws:SourceVpce` or `aws:SourceVpc` — those keys are set on VPC-
endpoint-routed requests, not AP-routed requests, and using them
produces a Deny that matches the wrong thing.

## 4. VPC endpoint policy — restrict bucket to AP-ARN access only

Applied to the VPC gateway endpoint for S3. Defense-in-depth for the
VPC-only invariant: even if a caller inside the VPC tries the global
hostname, the endpoint policy only allows the AP ARN.

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Sid": "AllowOnlyThroughAccessPoint",
    "Effect": "Allow",
    "Principal": "*",
    "Action": "s3:*",
    "Resource": [
      "arn:aws:s3:<REGION>:<ACCOUNT>:accesspoint/<AP_NAME>",
      "arn:aws:s3:<REGION>:<ACCOUNT>:accesspoint/<AP_NAME>/*"
    ]
  }]
}
```

Leave out the bucket ARN entirely — that forces all in-VPC traffic
through the AP.

## 5. Cross-account access point delegation

The BUCKET OWNER grants the foreign account `s3:CreateAccessPoint` in
the bucket policy. The foreign account then creates the AP and owns
its policy. The bucket owner CANNOT tighten the foreign-owned AP
policy directly; it must use a bucket-policy condition on the AP ARN
for containment.

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Sid": "DelegateAPCreation",
    "Effect": "Allow",
    "Principal": { "AWS": "arn:aws:iam::<FOREIGN_ACCOUNT>:root" },
    "Action": "s3:CreateAccessPoint",
    "Resource": "arn:aws:s3:::<BUCKET>"
  }]
}
```

For containment, the bucket owner adds a second statement restricting
what the foreign-owned AP can expose:

```json
{
  "Sid": "ContainForeignAP",
  "Effect": "Deny",
  "Principal": "*",
  "Action": "s3:*",
  "Resource": [
    "arn:aws:s3:::<BUCKET>",
    "arn:aws:s3:::<BUCKET>/sensitive/*"
  ],
  "Condition": {
    "StringEquals": {
      "s3:DataAccessPointAccount": "<FOREIGN_ACCOUNT>"
    }
  }
}
```

## 6. Object Lambda invocation policy

The transform Lambda's resource-based policy MUST grant the S3 Object
Lambda service principal `lambda:InvokeFunction` permission, or the
Object Lambda AP will throttle every request with `AccessDenied`.

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Sid": "AllowS3ObjectLambdaInvoke",
    "Effect": "Allow",
    "Principal": { "Service": "s3-object-lambda.amazonaws.com" },
    "Action": "lambda:InvokeFunction",
    "Resource": "<FUNC_ARN>"
  }]
}
```

## 7. S3 on Outposts AP policy

Outposts APs use the `arn:aws:s3-outposts:<region>:<account>:outpost/<id>/accesspoint/<name>`
ARN format. The policy structure is identical but the ARN namespace
differs — using the regional `s3control` API silently provisions
nothing on the Outpost.

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Sid": "OutpostAPRead",
    "Effect": "Allow",
    "Principal": { "AWS": "arn:aws:iam::<ACCOUNT>:role/OnPremAccessRole" },
    "Action": ["s3-outposts:GetObject", "s3-outposts:ListBucket"],
    "Resource": "arn:aws:s3-outposts:<REGION>:<ACCOUNT>:outpost/<OUTPOST_ID>/accesspoint/<AP_NAME>"
  }]
}
```
