from django.conf import settings
from ccwt.storages import AmazonS3Storage

kyc_file_storage = AmazonS3Storage(location=settings.KYC_DATA_LOCATION)
