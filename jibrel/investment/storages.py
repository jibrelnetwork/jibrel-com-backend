from django.conf import settings

from django_banking.storages import AmazonS3Storage

personal_agreements_file_storage = AmazonS3Storage(location=settings.PERSONAL_AGREEMENTS_DATA_LOCATION)
