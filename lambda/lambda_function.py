"""Bounded JPEG decoding; deterministic output makes duplicate events harmless."""
import io
import os
import warnings
from urllib.parse import unquote_plus
import boto3
from PIL import Image, ImageOps, UnidentifiedImageError

s3 = boto3.client('s3')
BUCKET = os.environ.get('BUCKET_NAME', '')
MAX_BYTES = 5 * 1024 * 1024
Image.MAX_IMAGE_PIXELS = 12_000_000


def lambda_handler(event, context):
    results = []
    for record in event.get('Records', []):
        bucket = record['s3']['bucket']['name']
        key = unquote_plus(record['s3']['object']['key'])
        if bucket != BUCKET or not key.startswith('originals/') or not key.endswith('.jpg'):
            continue
        obj = s3.get_object(Bucket=bucket, Key=key)
        try:
            if obj['ContentLength'] > MAX_BYTES:
                continue
            data = obj['Body'].read(MAX_BYTES + 1)
        finally:
            obj['Body'].close()
        if len(data) > MAX_BYTES:
            continue
        try:
            with warnings.catch_warnings():
                warnings.simplefilter('error', Image.DecompressionBombWarning)
                with Image.open(io.BytesIO(data)) as source:
                    if source.format != 'JPEG':
                        continue
                    img = ImageOps.exif_transpose(source).convert('RGB')
                    img.thumbnail((200, 200))
                    buf = io.BytesIO()
                    img.save(buf, 'JPEG', quality=85)
        except (UnidentifiedImageError, OSError, Image.DecompressionBombError, Image.DecompressionBombWarning, ValueError):
            print('Rejected invalid or oversized JPEG')
            continue
        thumb_key = 'thumbnails/' + key[len('originals/'):]
        s3.put_object(Bucket=bucket, Key=thumb_key, Body=buf.getvalue(),
                      ContentType='image/jpeg', CacheControl='private, max-age=300')
        results.append(thumb_key)
    return {'thumbnails': results}
