from storages.backends.s3boto3 import S3Boto3Storage
from ccwt.settings import (
    AWS_ACCESS_KEY_ID,
    AWS_SECRET_ACCESS_KEY,
    AWS_STORAGE_BUCKET_NAME,
    AWS_S3_REGION_NAME,
    AWS_QUERYSTRING_EXPIRE,
    OPERATION_UPLOAD_LOCATION
)


class AmazonS3Storage(S3Boto3Storage):
    access_key = AWS_ACCESS_KEY_ID
    secret_key = AWS_SECRET_ACCESS_KEY
    bucket_name = AWS_STORAGE_BUCKET_NAME
    region_name = AWS_S3_REGION_NAME
    querystring_expire = AWS_QUERYSTRING_EXPIRE
    file_overwrite = False


operation_upload_storage = AmazonS3Storage(location=OPERATION_UPLOAD_LOCATION)
