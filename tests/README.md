# Offline verification

Observed on 2026-11-06 in the Windows workspace:

- Python unittest discovery: 10 tests passed in 3.143 seconds. Pillow 12.3.0 performed actual in-memory JPEG conversion and resizing. S3 was mocked, so this does not verify AWS permissions, API routing or event delivery.
- Separate real botocore offline signing check: passed. Dummy credentials were used; no AWS requests were made. SigV4 includes content-length, content-type and host, with a 120-second expiry. Run with boto3/botocore installed: python tests/check_signing.py.
- CloudFormation/SAM template lint via cfn-lint: passed after correcting an initial control-character formatting issue. The ordinary cfn-lint launcher was blocked by Windows Application Control, so its Python entry point was invoked directly. python -m cfnlint is not supported by that package. This is static validation, not a CloudFormation deployment.
- The first real-SDK test imported boto3 and hit a Windows policy block on the multiprocessing DLL. Using botocore.session directly avoided that unrelated host dependency and the signing check then passed.

Coverage includes missing/wrong secrets; bounds and uniqueness for presigned uploads; gallery pagination; unknown routes; full-path thumbnail names; recursion/foreign-bucket guards; invalid/non-JPEG and oversized input rejection; duplicate event output; actual thumbnail dimensions.

Not performed: SAM container build, AWS deployment, live end-to-end S3/API tests, firmware compile or physical ESP32 test. SAM CLI, AWS CLI and Arduino CLI were not on PATH; Docker executable exists, but daemon readiness was not checked. The firmware also needs real private local configuration and verified CA certificates before it can work. API endpoints, secret, WiFi values and certificate in config.example.h are placeholders only.

Repeat with python -m unittest discover -s tests -v. Run template validation and container build in a configured deployment environment. Test malformed-image decompression limits and load/failure handling further before production use.
