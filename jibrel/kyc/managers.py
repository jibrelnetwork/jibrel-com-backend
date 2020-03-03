from django.db import models

from jibrel.kyc.enum import KYCSubmissionType


class IndividualKYCSubmissionManager(models.Manager):
    def create(self, **kwargs):
        kwargs['account_type'] = KYCSubmissionType.INDIVIDUAL
        return super(IndividualKYCSubmissionManager, self).create(**kwargs)
