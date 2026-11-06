import importlib.util
import io
import json
import os
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import Mock
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
# Stub SDK imports so tests need no AWS credentials, network or boto3 package.
sys.modules['boto3'] = types.SimpleNamespace(client=lambda *a, **k: Mock())
sys.modules['botocore'] = types.ModuleType('botocore')
sys.modules['botocore.config'] = types.SimpleNamespace(Config=lambda **kw: kw)
os.environ.update(BUCKET_NAME='test-bucket', DEVICE_SECRET='x' * 32)

def load(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

api = load('api_app', 'api/app.py')
thumb = load('thumb_app', 'lambda/lambda_function.py')

class ApiTests(unittest.TestCase):
    def setUp(self):
        api.s3 = Mock()
        api.s3.generate_presigned_url.return_value = 'https://example.invalid/signed'
        self.event = {'headers': {'X-Device-Secret': 'x' * 32, 'X-Image-Bytes': '123'},
                      'rawPath': '/presign', 'requestContext': {'http': {'method': 'POST'}}}
    def test_auth_and_fail_closed(self):
        self.event['headers'] = {}
        self.assertEqual(api.lambda_handler(self.event, None)['statusCode'], 401)
        self.event['headers'] = {'x-device-secret': 'wrong'}
        self.assertEqual(api.lambda_handler(self.event, None)['statusCode'], 401)
        api.s3.generate_presigned_url.assert_not_called()
    def test_unique_and_bounded_signed_upload(self):
        keys = []
        for _ in range(2):
            result = api.lambda_handler(self.event, None)
            self.assertEqual(result['statusCode'], 200)
            args = api.s3.generate_presigned_url.call_args.kwargs
            self.assertEqual(args['Params']['ContentLength'], 123)
            self.assertEqual(args['Params']['ContentType'], 'image/jpeg')
            self.assertEqual(args['ExpiresIn'], 120)
            keys.append(args['Params']['Key'])
        self.assertNotEqual(*keys)
        self.assertTrue(all(k.startswith('originals/') and k.endswith('.jpg') for k in keys))
    def test_invalid_sizes(self):
        for size in ('0', '-1', 'no', '5242881'):
            self.event['headers']['X-Image-Bytes'] = size
            self.assertEqual(api.lambda_handler(self.event, None)['statusCode'], 400)
    def test_gallery_pagination(self):
        self.event.update(rawPath='/gallery', queryStringParameters={'cursor': 'opaque'})
        self.event['requestContext']['http']['method'] = 'GET'
        api.s3.list_objects_v2.return_value = {'Contents': [{'Key': 'thumbnails/a.jpg', 'Size': 99}], 'NextContinuationToken': 'next'}
        result = api.lambda_handler(self.event, None)
        body = json.loads(result['body'])
        self.assertEqual(body['cursor'], 'next')
        self.assertEqual(len(body['items']), 1)
        api.s3.list_objects_v2.assert_called_once_with(Bucket='test-bucket', Prefix='thumbnails/', MaxKeys=30, ContinuationToken='opaque')
    def test_unknown_route(self):
        self.event['rawPath'] = '/unknown'
        self.assertEqual(api.lambda_handler(self.event, None)['statusCode'], 404)

class ThumbnailTests(unittest.TestCase):
    def setUp(self):
        thumb.s3 = Mock()
        self.event = {'Records': [{'s3': {'bucket': {'name': 'test-bucket'}, 'object': {'key': 'originals/2026/a.jpg'}}}]}
    def image(self, fmt='JPEG'):
        b = io.BytesIO()
        Image.new('RGB', (800, 400), 'red').save(b, fmt)
        return b.getvalue()
    def set_data(self, data, length=None):
        self.body = io.BytesIO(data)
        thumb.s3.get_object.return_value = {'Body': self.body, 'ContentLength': len(data) if length is None else length}
    def test_real_thumbnail_and_preserved_path(self):
        self.set_data(self.image())
        result = thumb.lambda_handler(self.event, None)
        self.assertEqual(result['thumbnails'], ['thumbnails/2026/a.jpg'])
        args = thumb.s3.put_object.call_args.kwargs
        with Image.open(io.BytesIO(args['Body'])) as im:
            self.assertEqual(im.size, (200, 100))
            self.assertEqual(im.format, 'JPEG')
        self.assertTrue(self.body.closed)
    def test_prefix_recursion_and_foreign_bucket(self):
        for bucket, key in [('test-bucket', 'thumbnails/a.jpg'), ('other', 'originals/a.jpg')]:
            self.event['Records'][0]['s3'] = {'bucket': {'name': bucket}, 'object': {'key': key}}
            self.assertEqual(thumb.lambda_handler(self.event, None)['thumbnails'], [])
        thumb.s3.get_object.assert_not_called()
    def test_bad_images_rejected(self):
        for data in (b'not an image', self.image('PNG')):
            self.set_data(data)
            self.assertEqual(thumb.lambda_handler(self.event, None)['thumbnails'], [])
        thumb.s3.put_object.assert_not_called()
    def test_oversize_rejected(self):
        self.set_data(b'x', 5242881)
        self.assertEqual(thumb.lambda_handler(self.event, None)['thumbnails'], [])
        self.assertTrue(self.body.closed)
        thumb.s3.put_object.assert_not_called()
    def test_duplicate_event_same_output_key(self):
        for _ in range(2):
            self.set_data(self.image())
            thumb.lambda_handler(self.event, None)
        self.assertEqual([c.kwargs['Key'] for c in thumb.s3.put_object.call_args_list], ['thumbnails/2026/a.jpg'] * 2)

if __name__ == '__main__':
    unittest.main()
