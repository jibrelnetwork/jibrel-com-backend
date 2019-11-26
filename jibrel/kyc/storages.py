from django.conf import settings
from django.core.files.storage import FileSystemStorage
from storages.backends.s3boto3 import S3Boto3Storage


class KYCAmazonS3Storage(S3Boto3Storage):
    location = settings.KYC_DATA_LOCATION
    access_key = settings.KYC_AWS_ACCESS_KEY_ID
    secret_key = settings.KYC_AWS_SECRET_ACCESS_KEY
    bucket_name = settings.KYC_AWS_STORAGE_BUCKET_NAME
    file_overwrite = False


file_storage = FileSystemStorage(location=settings.KYC_DATA_LOCATION)
if settings.KYC_DATA_USE_S3:
    file_storage = KYCAmazonS3Storage()
