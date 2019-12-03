from django.db import models


class IndividualKYCSubmissionManager(models.Manager):
    def create(self, **kwargs):
        from .models import IndividualKYCSubmission
        kwargs['account_type'] = IndividualKYCSubmission.INDIVIDUAL
        return super(IndividualKYCSubmissionManager, self).create(**kwargs)
