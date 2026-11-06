# IoT Image Gallery

Batch 36 · Project No. 02

An ESP32-CAM project with a public browser simulation and source for a private AWS upload/thumbnail pipeline.

## Live demo

https://koteshwarraoravipati-byte.github.io/iot-image-gallery/

Press the red button or Space to simulate capture, upload, LED confirmation and thumbnails. All demo images and metrics are generated in the browser; refreshing clears them. The demo does not connect to AWS.

## Project files

- `index.html`: standalone HTML/CSS/JavaScript demo, Chart.js 4.4.8.
- `firmware/`: ESP32-CAM source and a secret-free configuration example.
- `api/app.py`: header-authenticated presigned upload URL and gallery APIs.
- `lambda/`: bounded JPEG thumbnail processing with Pillow.
- `template.yaml`: AWS SAM infrastructure for private S3, API Gateway and Lambda.
- `tests/`: offline backend tests and signing checks.

## AWS deployment

See [DEPLOYMENT.md](DEPLOYMENT.md) for setup, security boundaries, testing and cleanup. AWS resources have not been deployed as part of this publishing step. The public demo remains a simulation. Never place a device secret, WiFi password, or AWS credentials in this website or repository.

Backend offline tests and static infrastructure lint passed during preparation; container build, cloud smoke tests and ESP32 compilation/flash remain unverified. AWS use may incur charges.

## Team

R. Koteshwar Rao, K. Siddhartha, R. Nagavignesh, S. Akshaya and E. Akshitha.

## GitHub Pages

Publish `main` from the repository root in Settings → Pages. `.nojekyll` keeps the site a plain static deployment.
