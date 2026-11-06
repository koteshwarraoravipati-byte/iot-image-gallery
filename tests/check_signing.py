"""Run separately with boto3 installed; uses dummy credentials and no AWS calls."""
from urllib.parse import urlparse, parse_qs
import botocore.session
from botocore.config import Config

client = botocore.session.get_session().create_client('s3', region_name='ap-south-1',
    aws_access_key_id='EXAMPLE_ONLY', aws_secret_access_key='EXAMPLE_ONLY',
    config=Config(signature_version='s3v4'))
url = client.generate_presigned_url('put_object', Params={
    'Bucket': 'example-iot-private-bucket', 'Key': 'originals/test.jpg',
    'ContentType': 'image/jpeg', 'ContentLength': 123}, ExpiresIn=120,
    HttpMethod='PUT')
query = parse_qs(urlparse(url).query)
assert query['X-Amz-SignedHeaders'] == ['content-length;content-type;host'], query
assert query['X-Amz-Expires'] == ['120'], query
print('PASS: real botocore signs content-length, content-type, host and 120-second expiry; no AWS calls')
