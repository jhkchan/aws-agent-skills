# Eval: wrong-platform-for-lambda

**Difficulty:** easy
**Branch:** PREREQUISITES_MISSING — AWSIoT profile cannot satisfy Lambda's verifier which expects AWSLambda-SHA384-ECDSA

## Prompt

Create a Signer signing profile "lambda-iot-wrong" on the AWSIoT
platform in us-east-1 and add it to the AllowedPublishingProfiles of
CSC "lambda-csc-prod" for function my-prod-function.
