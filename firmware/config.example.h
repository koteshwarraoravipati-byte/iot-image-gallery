#pragma once
// Copy to config.h locally. Never commit config.h or upload it to GitHub.
static const char WIFI_SSID[] = "YOUR_WIFI";
static const char WIFI_PASS[] = "YOUR_WIFI_PASSWORD";
static const char PRESIGN_API[] = "https://YOUR_API_ID.execute-api.ap-south-1.amazonaws.com/presign";
static const char DEVICE_SECRET[] = "REPLACE_WITH_THE_DEPLOYED_RANDOM_SECRET";
// Paste the currently trusted root CA PEM(s) for BOTH API Gateway and regional S3.
// Get certificates from the issuing CA's official repository, verify fingerprints
// independently, and plan certificate/root updates. Do NOT use setInsecure().
static const char AWS_ROOT_CA[] = R"PEM(
-----BEGIN CERTIFICATE-----
REPLACE_WITH_VERIFIED_ROOT_CA_PEM
-----END CERTIFICATE-----
)PEM";
