# Eval: nodejs-sdk-layer

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — Node.js SDK layer for nodejs20.x + nodejs22.x (which don't bundle the AWS SDK by default), x86_64, correct zip path (nodejs/node_modules/)

## Prompt

I need a Node.js Lambda Layer named "sdk-layer" in us-east-1
that bundles @aws-sdk/client-s3, @aws-sdk/client-dynamodb, and
@aws-sdk/lib-dynamodb for Node.js 22 functions (which don't
bundle the SDK by default). Compatible runtimes: nodejs20.x and
nodejs22.x. Architecture: x86_64. License: Apache-2.0. Account
ID: 123456789012.
