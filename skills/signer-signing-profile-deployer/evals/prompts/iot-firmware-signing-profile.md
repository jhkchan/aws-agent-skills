# Eval: iot-firmware-signing-profile

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — AWSIoT platform (NOT valid for Lambda CSC), OTA consumption flow, firmware source/destination

## Prompt

Create a Signer signing profile "iot-firmware-prod" on the AWSIoT
platform in us-east-1, account 111122223333. Source bucket
my-unsigned-firmware, destination bucket my-signed-firmware with
prefix firmware/signed/. This profile will be used by AWS IoT OTA
update jobs. Tags: Environment=production, Workload=iot-firmware.
