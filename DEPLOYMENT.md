# Deploy the private AWS pipeline

This is deployment-ready source, not evidence of a deployed service. The root index.html is still a browser simulation. It does not call these APIs. Do not put DEVICE_SECRET in that public page or any browser bundle.

## Prerequisites and build

Use an AWS account you control, AWS CLI v2 configured for the intended account, AWS SAM CLI, and Docker. Check the account with aws sts get-caller-identity before deployment. The default example region is ap-south-1. Run commands from the repository root after merging these files.

Use a short lowercase stack name such as iot-gallery-demo (at most 30 characters; letters, numbers and hyphens). The stack creates a globally unique bucket name from that name, account ID and region.

1. Run `sam validate --lint`, then `sam build --use-container`. Audit the pinned dependency for security updates before production use. The container build installs the pinned Pillow dependency for Lambda Linux x86_64, rather than copying Windows wheels.
2. Generate a random secret of at least 32 characters in a password manager. Do not reuse a WiFi or AWS password.
3. Run `sam deploy --guided`. Choose the stack name and region, enter DeviceSecret when prompted, allow IAM role creation, and review the change set before applying it. Do not save the secret in samconfig.toml, terminal commands, screenshots, build artifacts or Git. NoEcho masks CloudFormation parameter display but is not a secret vault. If guided deployment saves parameter overrides, decline config saving and delete any secret-bearing config locally.
4. Record ApiBaseUrl and BucketName from stack outputs. These identifiers are not credentials. Set a small AWS Budget with notifications and check its delivery; a Budget alert does not cap spending.

SAM creates a private encrypted S3 bucket, HTTPS-only bucket policy, an HTTP API, least-scope data permissions, two Lambda functions, S3 event wiring and 14-day log retention. Originals and thumbnails expire after 30 days. The thumbnail event watches originals/ plus .jpg; output goes under thumbnails/ with the full unique path preserved.

## Device setup

Copy firmware/config.example.h to firmware/config.h and fill it locally. Keep config.h ignored. Use the same DeviceSecret as the stack parameter and append /presign to ApiBaseUrl. Paste verified CA root PEMs that validate both the API Gateway endpoint and regional S3 endpoint into AWS_ROOT_CA; concatenated roots are supported. The template placeholder is deliberately not a working certificate. Never replace this with setInsecure().

Build with the Arduino ESP32 core 3.x, AI Thinker ESP32-CAM board, PSRAM enabled when available, and the matching esp_camera library supplied by that core. This firmware has not been hardware-compiled or flashed in this workspace. Confirm field names against your installed core if using another version. A working network and NTP time sync are required before capture. WiFi retries every ten seconds without blocking boot. Upload failure is not retried automatically or queued offline.

GPIO12 is an ESP32 boot-strapping pin; an external LED circuit must not pull it high during reset. GPIO13 conflicts with SD card use on common boards. Use a suitable resistor and stable board-appropriate supply; verify wiring before powering hardware. The success LED confirms S3 accepted the original, not that thumbnail generation has completed.

## API contract and smoke test

No AWS credentials belong in the firmware. The device sends POST /presign with X-Device-Secret and X-Image-Bytes headers. The body can be empty. The response is a plain-text, 120-second S3 PUT URL with an exact signed Content-Length and image/jpeg Content-Type. Names supplied by clients are ignored; the API generates a UTC-date/UUID key. PUT the exact JPEG bytes with Content-Type: image/jpeg and their exact Content-Length. A new URL is needed after expiry.

GET /gallery requires the same X-Device-Secret header. It returns up to 30 thumbnail entries with five-minute signed GET URLs and an opaque cursor. URL-encode the returned cursor as the next cursor query parameter. Listing is S3 key order (oldest date first), not newest-first. An upload can take several seconds to appear. This demo shares one secret across upload and read access; use separate principals/scopes for a multi-user product.

A safe live acceptance test, after approving deployment:

- Call POST /presign with no secret and with an incorrect secret; both must return 401.
- Call it with a valid secret and X-Image-Bytes equal to a small local JPEG file size; expect 200 and an HTTPS URL.
- PUT that JPEG with the exact content type and length; expect 200. A mismatched signed length should fail.
- Wait, then call GET /gallery with the secret. Download one returned URL and check the JPEG dimensions are at most 200 by 200.
- Confirm anonymous direct bucket reads fail, no thumbnails invoke recursive processing, and application logs do not contain secrets or signed URLs.

Use a local script that reads secrets interactively or from a secure environment. Do not paste live signed URLs into public issues. HTTP requests from the public simulation are intentionally not enabled: there is no CORS policy. CORS is not authentication. A real web gallery should use user login (for example Cognito) or a server-side session proxy, rather than a device secret exposed to visitors.

## Costs and security boundaries

This is not a free hosting guarantee. Charges can include API Gateway requests, Lambda requests/compute, S3 writes/reads/storage, CloudWatch logs, internet data transfer and SAM deployment artifacts. Region, traffic, image size and AWS account offers determine the bill. No dollar estimate is asserted here. No NAT gateway, public bucket or paid custom domain is created. Storage expiration and log retention limit accumulation but not request spikes.

The API rate limit is a best-effort throttle, not a billing cap. Lambda reserved concurrency is not set, because low-quota new accounts may not permit reservations; set appropriate account/function limits after checking your quotas. Invalid-secret traffic still invokes Lambda. One shared device secret is a prototype control, not device attestation; extracting it from firmware allows upload and gallery access until rotation. Rotate by updating the stack parameter and devices. Lambda environment variables are encrypted at rest but readable to authorized account administrators; use Secrets Manager/per-device identity for a production fleet. Enable ESP32 flash encryption/secure boot where appropriate after reviewing provisioning consequences.

Signed URLs are bearer tokens until expiry and a PUT URL can overwrite its own unique key during that interval. Content-Length signing bounds authorized upload size, but S3 cannot verify that image/jpeg bytes are actually a JPEG. The worker rejects malformed images and limits compressed bytes and decoded pixels; rejected originals remain private until lifecycle expiry. JPEG re-encoding strips metadata from thumbnails, not from originals. Avoid sensitive images without a retention/privacy policy. Repeated S3 events overwrite the same thumbnail safely; an original overwritten during the URL validity window can create races. This is acceptable for a small demo, not immutable evidence storage. There is no WAF, user account management, malware scanner, per-device quota, DLQ, audit dashboard or production alarm package in this sample. Configure alerting and failure destinations before production use.

## Tests and cleanup

Run `python -m unittest discover -s tests -v` with Pillow available. Tests use mocked S3 and do not contact AWS. See tests/README.md for actual observed results and limits. Do not describe offline tests as a cloud deployment or an ESP32 hardware test.

Delete uploaded images and thumbnails before `sam delete --stack-name iot-gallery-demo --region ap-south-1`: CloudFormation cannot delete a nonempty bucket. Review and remove deployment artifact buckets/objects as appropriate; shared SAM-managed artifact buckets may serve other stacks. Logs and deployment artifacts may need separate cleanup depending on deployment history. Stack deletion is destructive; keep anything you need first.
