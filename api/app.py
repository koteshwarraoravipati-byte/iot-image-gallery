"""Header-authenticated, short-lived upload and gallery URLs. No browser CORS."""
import hmac
import json
import os
import uuid
from datetime import datetime, timezone
import boto3
from botocore.config import Config

s3 = boto3.client('s3', config=Config(signature_version='s3v4'))
BUCKET = os.environ.get('BUCKET_NAME', '')
MAX_BYTES = 5 * 1024 * 1024


def response(status, body, content_type='application/json'):
    return {'statusCode': status, 'headers': {
        'Content-Type': content_type, 'Cache-Control': 'no-store',
        'X-Content-Type-Options': 'nosniff'},
        'body': json.dumps(body) if content_type == 'application/json' else body}


def lambda_handler(event, context):
    headers = {k.lower(): v for k, v in (event.get('headers') or {}).items()}
    secret = os.environ.get('DEVICE_SECRET', '')
    supplied = headers.get('x-device-secret', '')
    if not secret or not hmac.compare_digest(supplied.encode(), secret.encode()):
        return response(401, {'error': 'Unauthorized'})
    method = event.get('requestContext', {}).get('http', {}).get('method')
    path = event.get('rawPath', '')
    if method == 'POST' and path == '/presign':
        try:
            length = int(headers.get('x-image-bytes', '0'))
        except (ValueError, TypeError):
            length = 0
        if not 0 < length <= MAX_BYTES:
            return response(400, {'error': 'X-Image-Bytes must be 1..5242880'})
        key = 'originals/' + datetime.now(timezone.utc).strftime('%Y/%m/%d/') + uuid.uuid4().hex + '.jpg'
        url = s3.generate_presigned_url('put_object', Params={
            'Bucket': BUCKET, 'Key': key, 'ContentType': 'image/jpeg',
            'ContentLength': length}, ExpiresIn=120, HttpMethod='PUT')
        return response(200, url, 'text/plain')
    if method == 'GET' and path == '/gallery':
        params = event.get('queryStringParameters') or {}
        args = {'Bucket': BUCKET, 'Prefix': 'thumbnails/', 'MaxKeys': 30}
        if params.get('cursor'):
            if len(params['cursor']) > 4096:
                return response(400, {'error': 'Invalid cursor'})
            args['ContinuationToken'] = params['cursor']
        try:
            result = s3.list_objects_v2(**args)
        except s3.exceptions.ClientError as exc:
            if exc.response.get('Error', {}).get('Code') in ('InvalidArgument', 'InvalidToken'):
                return response(400, {'error': 'Invalid cursor'})
            raise
        items = [{'key': item['Key'], 'bytes': item['Size'],
                  'url': s3.generate_presigned_url('get_object', Params={
                      'Bucket': BUCKET, 'Key': item['Key']}, ExpiresIn=300)}
                 for item in result.get('Contents', [])]
        return response(200, {'items': items, 'cursor': result.get('NextContinuationToken')})
    return response(404, {'error': 'Not found'})
