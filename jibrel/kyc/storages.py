from django.conf import settings
from storages.backends.s3boto3 import S3Boto3Storage


class KYCAmazonS3Storage(S3Boto3Storage):
    location = settings.KYC_DATA_LOCATION
    access_key = settings.AWS_ACCESS_KEY_ID
    secret_key = settings.AWS_SECRET_ACCESS_KEY
    bucket_name = settings.AWS_STORAGE_BUCKET_NAME
    default_acl = 'private'

    file_overwrite = False


file_storage = KYCAmazonS3Storage()
