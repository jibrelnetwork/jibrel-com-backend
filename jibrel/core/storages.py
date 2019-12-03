from django.conf import settings
from storages.backends.s3boto3 import S3Boto3Storage


class AmazonS3Storage(S3Boto3Storage):
    access_key = settings.AWS_ACCESS_KEY_ID
    secret_key = settings.AWS_SECRET_ACCESS_KEY
    bucket_name = settings.AWS_STORAGE_BUCKET_NAME
    region_name = settings.AWS_S3_REGION_NAME
    querystring_expire = settings.AWS_QUERYSTRING_EXPIRE
    file_overwrite = False


kyc_file_storage = AmazonS3Storage(location=settings.KYC_DATA_LOCATION)

operation_upload_storage = AmazonS3Storage(location=settings.OPERATION_UPLOAD_LOCATION)
