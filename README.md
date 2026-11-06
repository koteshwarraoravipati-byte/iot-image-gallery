# IoT Image Gallery

**Batch 36 · Project No. 02**

> Press a button to capture an event, an LED confirms upload, and the image is auto‑thumbnailed by AWS Lambda.

## Team
| # | Name |
|---|------|
| 1 | R. Koteshwar Rao |
| 2 | K. Siddhartha |
| 3 | R. Nagavignesh |
| 4 | S. Akshaya |
| 5 | E. Akshitha |

## How it works
1. **Button press** on GPIO13 of an ESP32‑CAM triggers an interrupt.
2. The **OV2640 camera** captures a JPEG.
3. The device **uploads** the image to an S3 bucket (`originals/`) over HTTPS.
4. On HTTP 200, a **green LED** (GPIO12) lights up to confirm the upload.
5. The S3 `ObjectCreated` event invokes an **AWS Lambda** function that creates a thumbnail in `thumbnails/`.
6. The **web dashboard** (`index.html`) shows the pipeline, stats and thumbnail gallery.

## Repo structure
```
index.html                  Dashboard website (GitHub Pages)
firmware/iot_gallery.ino    ESP32‑CAM firmware (Arduino)
lambda/lambda_function.py   Thumbnail generator (Python + Pillow)
```

## Live demo
The dashboard includes a browser simulation of the device and cloud pipeline. Press the red button or hit **Space**.

## Deploy (GitHub Pages)
Settings → Pages → Source: *Deploy from a branch* → `main` / `(root)` → Save.
Site URL: `https://<your-username>.github.io/iot-image-gallery/`

## AWS setup (summary)
1. Create S3 bucket `iot-gallery-<yourname>` with folders `originals/` and `thumbnails/`.
2. Create Lambda (Python 3.12), attach a Pillow layer, paste `lambda/lambda_function.py`.
3. Add S3 trigger: event `PUT`, prefix `originals/`.
4. Give the Lambda role `s3:GetObject` on `originals/*` and `s3:PutObject` on `thumbnails/*`.
